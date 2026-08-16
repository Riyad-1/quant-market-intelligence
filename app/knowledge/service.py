"""RAG-based research service for answering questions with sourced evidence."""

import logging
from dataclasses import dataclass
from typing import Any

from app.llm.base import LLMProvider
from app.llm.prompts import RESEARCH_SYSTEM_PROMPT, RESEARCH_USER_TEMPLATE
from app.retrieval.base import RetrievalProvider, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class ResearchAnswer:
    """A research answer with sources and confidence."""

    answer: str
    sources: list[dict[str, Any]]
    confidence: float
    has_sufficient_evidence: bool
    contradictions_identified: bool = False
    ambiguities_identified: bool = False


class ResearchService:
    """Service for answering research questions using RAG."""

    def __init__(
        self,
        retrieval_provider: RetrievalProvider,
        llm_provider: LLMProvider,
        top_k: int = 10,
        max_context_length: int = 8000,
    ) -> None:
        """Initialize research service.

        Args:
            retrieval_provider: Provider for retrieving relevant documents.
            llm_provider: Provider for generating answers.
            top_k: Number of documents to retrieve.
            max_context_length: Maximum context length for LLM.
        """
        self._retrieval_provider = retrieval_provider
        self._llm_provider = llm_provider
        self._top_k = top_k
        self._max_context_length = max_context_length

    def _format_sources(self, results: list[SearchResult]) -> tuple[str, list[dict[str, Any]]]:
        """Format search results into context string and source metadata.

        Args:
            results: List of search results.

        Returns:
            Tuple of (context_string, sources_metadata)
        """
        context_parts = []
        sources = []

        for i, result in enumerate(results, 1):
            # Build source citation
            source_info = {
                "index": i,
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "document_title": result.document_title or "Unknown",
                "document_author": result.document_author or "Unknown",
                "page_start": result.page_start,
                "page_end": result.page_end,
                "section_heading": result.section_heading,
                "score": result.score,
            }

            # Format page reference
            page_ref = ""
            if result.page_start is not None:
                if result.page_end is not None and result.page_end != result.page_start:
                    page_ref = f" (pages {result.page_start}-{result.page_end})"
                else:
                    page_ref = f" (page {result.page_start})"

            # Add section info if available
            section_ref = ""
            if result.section_heading:
                section_ref = f" - Section: {result.section_heading}"

            # Build header for this source
            header = f"[Source {i}] {source_info['document_title']}"
            if source_info['document_author'] and source_info['document_author'] != "Unknown":
                header += f" by {source_info['document_author']}"
            header += page_ref + section_ref
            header += f" (relevance: {result.score:.2f})\n\n"

            # Add the text content
            context_parts.append(f"{header}{result.text}\n")
            sources.append(source_info)

        return "\n".join(context_parts), sources

    async def query(self, question: str) -> ResearchAnswer:
        """Answer a research question using retrieved source material.

        Args:
            question: The research question to answer.

        Returns:
            ResearchAnswer with answer, sources, and metadata.
        """
        # Step 1: Retrieve relevant documents
        search_query = SearchQuery(query=question, top_k=self._top_k)
        
        try:
            results = await self._retrieval_provider.search(search_query)
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return ResearchAnswer(
                answer=f"Error retrieving source material: {str(e)}",
                sources=[],
                confidence=0.0,
                has_sufficient_evidence=False,
            )

        if not results:
            return ResearchAnswer(
                answer="No relevant source material was found to answer this question.",
                sources=[],
                confidence=0.0,
                has_sufficient_evidence=False,
            )

        # Step 2: Format sources into context
        context, sources = self._format_sources(results)

        # Check if we have enough context
        if len(context.strip()) < 50:
            return ResearchAnswer(
                answer="The retrieved source material appears to be insufficient to answer this question.",
                sources=sources,
                confidence=0.0,
                has_sufficient_evidence=False,
            )

        # Truncate context if too long
        if len(context) > self._max_context_length:
            context = context[: self._max_context_length] + "\n... [truncated]"
            logger.warning(f"Context truncated to {self._max_context_length} characters")

        # Step 3: Generate answer using LLM
        user_prompt = RESEARCH_USER_TEMPLATE.format(question=question, context=context)

        try:
            answer = await self._llm_provider.generate_completion(
                prompt=user_prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.1,  # Low temperature for factual accuracy
                max_tokens=2048,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ResearchAnswer(
                answer=f"Error generating answer: {str(e)}",
                sources=sources,
                confidence=0.0,
                has_sufficient_evidence=len(results) > 0,
            )

        # Step 4: Analyze the answer for confidence indicators
        has_sufficient = (
            "insufficient" not in answer.lower() 
            and "not contain sufficient" not in answer.lower()
        )
        contradictions = "contradict" in answer.lower() or "however" in answer.lower()
        ambiguities = "unclear" in answer.lower() or "ambiguous" in answer.lower()

        # Calculate rough confidence based on source scores
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        confidence = min(avg_score * 1.2, 1.0) if has_sufficient else 0.0

        return ResearchAnswer(
            answer=answer,
            sources=sources,
            confidence=confidence,
            has_sufficient_evidence=has_sufficient,
            contradictions_identified=contradictions,
            ambiguities_identified=ambiguities,
        )
