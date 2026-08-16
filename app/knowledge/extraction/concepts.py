"""Concept extraction service.

This service extracts trading concepts from source material using LLM-based analysis.
Each extracted concept is linked to its evidence (document chunks) for provenance.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Concept, ConceptEvidence, ConceptRelation, DocumentChunk
from app.knowledge.schemas import ConceptCreate, ConceptRelationCreate
from app.llm.base import LLMProvider
from app.llm.prompts import CONCEPT_EXTRACTION_SYSTEM, CONCEPT_EXTRACTION_USER_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class ExtractedConcept:
    """A concept extracted from source material."""

    name: str
    description: str | None
    category: str
    related_concepts: list[str]
    source_reference: str | None
    chunk_id: int


@dataclass
class ConceptExtractionResult:
    """Result of concept extraction from a chunk."""

    concepts: list[ExtractedConcept]
    chunk_id: int
    success: bool
    error_message: str | None = None


class ConceptExtractionService:
    """Service for extracting trading concepts from document chunks."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_concepts_per_chunk: int = 10,
    ) -> None:
        """Initialize concept extraction service.

        Args:
            llm_provider: LLM provider for extraction.
            max_concepts_per_chunk: Maximum concepts to extract per chunk.
        """
        self._llm_provider = llm_provider
        self._max_concepts = max_concepts_per_chunk

    async def extract_from_chunk(
        self,
        session: AsyncSession,
        chunk_id: int,
    ) -> ConceptExtractionResult:
        """Extract concepts from a single document chunk.

        Args:
            session: Database session.
            chunk_id: ID of the chunk to analyze.

        Returns:
            ConceptExtractionResult with extracted concepts.
        """
        # Fetch the chunk
        result = await session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.id == chunk_id)
            .options(
                # Load document info for context
            )
        )
        chunk = result.scalar_one_or_none()

        if not chunk:
            return ConceptExtractionResult(
                concepts=[],
                chunk_id=chunk_id,
                success=False,
                error_message=f"Chunk {chunk_id} not found",
            )

        # Build prompt with chunk text and metadata
        page_range = ""
        if chunk.page_start is not None:
            if chunk.page_end is not None and chunk.page_end != chunk.page_start:
                page_range = f"{chunk.page_start}-{chunk.page_end}"
            else:
                page_range = str(chunk.page_start)

        # Get document info via relationship
        doc_result = await session.execute(
            select(DocumentChunk.document_id, DocumentChunk.section_id).where(
                DocumentChunk.id == chunk_id
            )
        )
        doc_row = doc_result.first()
        if not doc_row:
            return ConceptExtractionResult(
                concepts=[],
                chunk_id=chunk_id,
                success=False,
                error_message="Could not fetch document info",
            )

        document_id = doc_row.document_id
        doc_info_result = await session.execute(
            select(
                # Would need to join with Document table
            )
        )

        user_prompt = CONCEPT_EXTRACTION_USER_TEMPLATE.format(
            text=chunk.text,
            document_title=f"Document {document_id}",
            author="Unknown",
            page_range=page_range or "Unknown",
        )

        try:
            # Call LLM to extract concepts
            response = await self._llm_provider.generate_completion(
                prompt=user_prompt,
                system_prompt=CONCEPT_EXTRACTION_SYSTEM,
                temperature=0.1,
                max_tokens=2048,
            )

            # Parse the JSON response
            import json

            try:
                extracted_data = json.loads(response)
                concepts_data = extracted_data.get("concepts", [])
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                # Try to extract concepts manually or return empty
                return ConceptExtractionResult(
                    concepts=[],
                    chunk_id=chunk_id,
                    success=False,
                    error_message=f"Failed to parse LLM response: {e}",
                )

            # Convert to ExtractedConcept objects
            extracted_concepts: list[ExtractedConcept] = []
            for c in concepts_data[: self._max_concepts]:
                extracted_concepts.append(
                    ExtractedConcept(
                        name=c.get("name", ""),
                        description=c.get("description"),
                        category=c.get("category", "other"),
                        related_concepts=c.get("related_concepts", []),
                        source_reference=c.get("source_reference"),
                        chunk_id=chunk_id,
                    )
                )

            return ConceptExtractionResult(
                concepts=extracted_concepts,
                chunk_id=chunk_id,
                success=True,
            )

        except Exception as e:
            logger.error(f"Concept extraction failed for chunk {chunk_id}: {e}")
            return ConceptExtractionResult(
                concepts=[],
                chunk_id=chunk_id,
                success=False,
                error_message=str(e),
            )

    async def save_concept(
        self,
        session: AsyncSession,
        concept: ExtractedConcept,
        review_status: str = "PROPOSED",
    ) -> Concept:
        """Save an extracted concept to the database.

        Args:
            session: Database session.
            concept: The extracted concept to save.
            review_status: Initial review status.

        Returns:
            The saved Concept object.
        """
        # Check if concept with same name already exists
        existing = await session.execute(
            select(Concept).where(Concept.name.ilike(concept.name))
        )
        existing_concept = existing.scalar_one_or_none()

        if existing_concept:
            # Concept exists - just add evidence link
            logger.info(f"Concept '{concept.name}' already exists, adding evidence")
            concept_obj = existing_concept
        else:
            # Create new concept
            concept_obj = Concept(
                name=concept.name,
                description=concept.description,
                category=concept.category,
                review_status=review_status,
                metadata_json={
                    "source_reference": concept.source_reference,
                    "related_concepts": concept.related_concepts,
                },
            )
            session.add(concept_obj)
            await session.flush()
            logger.info(f"Created new concept: {concept.name}")

        # Add evidence link
        evidence = ConceptEvidence(
            concept_id=concept_obj.id,
            chunk_id=concept.chunk_id,
            excerpt=concept.source_reference,
        )
        session.add(evidence)

        return concept_obj

    async def save_concept_relations(
        self,
        session: AsyncSession,
        concept: Concept,
        related_names: list[str],
    ) -> list[ConceptRelation]:
        """Save relationships between concepts.

        Args:
            session: Database session.
            concept: The source concept.
            related_names: Names of related concepts.

        Returns:
            List of created ConceptRelation objects.
        """
        relations: list[ConceptRelation] = []

        for related_name in related_names:
            # Find the target concept
            target_result = await session.execute(
                select(Concept).where(Concept.name.ilike(related_name))
            )
            target_concept = target_result.scalar_one_or_none()

            if not target_concept:
                # Create the related concept if it doesn't exist
                target_concept = Concept(
                    name=related_name,
                    category="other",
                    review_status="PROPOSED",
                )
                session.add(target_concept)
                await session.flush()

            # Check if relation already exists
            existing = await session.execute(
                select(ConceptRelation).where(
                    ConceptRelation.source_concept_id == concept.id,
                    ConceptRelation.target_concept_id == target_concept.id,
                    ConceptRelation.relation_type == "RELATED_TO",
                )
            )

            if not existing.scalar_one_or_none():
                relation = ConceptRelation(
                    source_concept_id=concept.id,
                    target_concept_id=target_concept.id,
                    relation_type="RELATED_TO",
                )
                session.add(relation)
                relations.append(relation)

        return relations

    async def extract_and_save_from_chunks(
        self,
        session: AsyncSession,
        chunk_ids: list[int],
    ) -> dict[str, int]:
        """Extract concepts from multiple chunks and save to database.

        Args:
            session: Database session.
            chunk_ids: List of chunk IDs to process.

        Returns:
            Dictionary with statistics.
        """
        stats = {
            "chunks_processed": 0,
            "chunks_failed": 0,
            "concepts_extracted": 0,
            "concepts_created": 0,
            "relations_created": 0,
        }

        for chunk_id in chunk_ids:
            result = await self.extract_from_chunk(session, chunk_id)

            if not result.success:
                stats["chunks_failed"] += 1
                continue

            stats["chunks_processed"] += 1

            for concept in result.concepts:
                stats["concepts_extracted"] += 1

                # Save concept
                concept_obj = await self.save_concept(session, concept)

                # Check if it was newly created
                existing_check = await session.execute(
                    select(Concept).where(Concept.id == concept_obj.id)
                )
                # This is a simplification - in reality we'd track this differently

                # Save relations
                relations = await self.save_concept_relations(
                    session, concept_obj, concept.related_concepts
                )
                stats["relations_created"] += len(relations)

        return stats
