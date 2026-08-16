"""Strategy extraction service.

This service extracts trading strategies from source material using LLM-based analysis.
Each extracted strategy and its rules are linked to evidence (document chunks) for provenance.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    Concept,
    Document,
    DocumentChunk,
    Hypothesis,
    HypothesisEvidence,
    RuleCategory,
    RuleClassification,
    RuleEvidence,
    Strategy,
    StrategyEvidence,
    StrategyRule,
    Trader,
)
from app.knowledge.schemas import StrategyCreate, StrategyRuleCreate
from app.llm.base import LLMProvider
from app.llm.prompts import STRATEGY_EXTRACTION_SYSTEM, STRATEGY_EXTRACTION_USER_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class ExtractedStrategyRule:
    """A rule extracted from strategy source material."""

    rule_text: str
    category: str  # technical, fundamental, setup, entry, exit, etc.
    classification: str  # objective, subjective, unresolved
    numeric_definition: str | None
    source_reference: str | None
    chunk_id: int


@dataclass
class ExtractedStrategy:
    """A strategy extracted from source material."""

    name: str
    description: str | None
    trader_name: str | None
    timeframe: str | None
    strategy_type: str | None
    philosophy: str | None
    rules: list[ExtractedStrategyRule]
    market_regime_requirements: list[str]
    exceptions: list[str]
    ambiguities: list[str]
    source_references: list[str]
    chunk_id: int


@dataclass
class StrategyExtractionResult:
    """Result of strategy extraction from a chunk or document."""

    strategy: ExtractedStrategy | None
    chunk_id: int | None
    success: bool
    error_message: str | None = None


class StrategyExtractionService:
    """Service for extracting trading strategies from document chunks."""

    def __init__(
        self,
        llm_provider: LLMProvider,
    ) -> None:
        """Initialize strategy extraction service.

        Args:
            llm_provider: LLM provider for extraction.
        """
        self._llm_provider = llm_provider

    async def extract_from_chunks(
        self,
        session: AsyncSession,
        chunk_ids: list[int],
        trader_name: str | None = None,
    ) -> StrategyExtractionResult:
        """Extract a strategy from multiple document chunks.

        Args:
            session: Database session.
            chunk_ids: List of chunk IDs containing strategy information.
            trader_name: Optional name of trader/investor associated with strategy.

        Returns:
            StrategyExtractionResult with extracted strategy.
        """
        # Fetch all chunks
        result = await session.execute(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        )
        chunks = result.scalars().all()

        if not chunks:
            return StrategyExtractionResult(
                strategy=None,
                chunk_id=None,
                success=False,
                error_message="No chunks found",
            )

        # Combine chunk texts
        combined_text = "\n\n".join([chunk.text for chunk in chunks])
        primary_chunk_id = chunks[0].id

        # Get document info for first chunk
        first_chunk = chunks[0]
        doc_result = await session.execute(
            select(Document).where(Document.id == first_chunk.document_id)
        )
        document = doc_result.scalar_one_or_none()

        document_title = document.title if document else "Unknown"
        document_author = document.author if document else "Unknown"

        # Build prompt
        user_prompt = STRATEGY_EXTRACTION_USER_TEMPLATE.format(
            text=combined_text,
            document_title=document_title,
            author=document_author or "Unknown",
            trader_name=trader_name or "Unknown",
            page_range="",
        )

        try:
            # Call LLM to extract strategy
            response = await self._llm_provider.generate_completion(
                prompt=user_prompt,
                system_prompt=STRATEGY_EXTRACTION_SYSTEM,
                temperature=0.1,
                max_tokens=4096,
            )

            # Parse the JSON response
            import json

            try:
                extracted_data = json.loads(response)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                return StrategyExtractionResult(
                    strategy=None,
                    chunk_id=primary_chunk_id,
                    success=False,
                    error_message=f"Failed to parse LLM response: {e}",
                )

            # Convert to ExtractedStrategy
            rules_data = extracted_data.get("setup_conditions", [])
            rules_data.extend(extracted_data.get("entry_conditions", []))
            rules_data.extend(extracted_data.get("exit_conditions", []))
            rules_data.extend(extracted_data.get("stop_loss_rules", []))
            rules_data.extend(extracted_data.get("position_sizing_rules", []))

            extracted_rules: list[ExtractedStrategyRule] = []
            for r in rules_data:
                extracted_rules.append(
                    ExtractedStrategyRule(
                        rule_text=r.get("rule", ""),
                        category=r.get("type", "other"),
                        classification=r.get("classification", "unresolved"),
                        numeric_definition=r.get("numeric_definition"),
                        source_reference=r.get("source_reference"),
                        chunk_id=primary_chunk_id,
                    )
                )

            strategy = ExtractedStrategy(
                name=extracted_data.get("strategy_name", "Unnamed Strategy"),
                description=extracted_data.get("philosophy"),
                trader_name=trader_name,
                timeframe=extracted_data.get("timeframe"),
                strategy_type=None,  # Could be inferred later
                philosophy=extracted_data.get("philosophy"),
                rules=extracted_rules,
                market_regime_requirements=extracted_data.get("market_regime_requirements", []),
                exceptions=extracted_data.get("exceptions", []),
                ambiguities=extracted_data.get("ambiguities", []),
                source_references=extracted_data.get("source_references", []),
                chunk_id=primary_chunk_id,
            )

            return StrategyExtractionResult(
                strategy=strategy,
                chunk_id=primary_chunk_id,
                success=True,
            )

        except Exception as e:
            logger.error(f"Strategy extraction failed: {e}")
            return StrategyExtractionResult(
                strategy=None,
                chunk_id=primary_chunk_id,
                success=False,
                error_message=str(e),
            )

    async def _get_or_create_trader(
        self,
        session: AsyncSession,
        trader_name: str,
    ) -> Trader:
        """Get existing trader or create new one.

        Args:
            session: Database session.
            trader_name: Name of the trader.

        Returns:
            Trader object.
        """
        existing = await session.execute(
            select(Trader).where(Trader.name.ilike(trader_name))
        )
        trader = existing.scalar_one_or_none()

        if not trader:
            trader = Trader(name=trader_name)
            session.add(trader)
            await session.flush()
            logger.info(f"Created new trader: {trader_name}")

        return trader

    async def save_strategy(
        self,
        session: AsyncSession,
        strategy: ExtractedStrategy,
        review_status: str = "PROPOSED",
    ) -> Strategy:
        """Save an extracted strategy to the database.

        Args:
            session: Database session.
            strategy: The extracted strategy to save.
            review_status: Initial review status.

        Returns:
            The saved Strategy object.
        """
        # Get or create trader
        trader_id = None
        if strategy.trader_name:
            trader = await self._get_or_create_trader(session, strategy.trader_name)
            trader_id = trader.id

        # Create strategy
        strategy_obj = Strategy(
            name=strategy.name,
            description=strategy.description,
            trader_id=trader_id,
            timeframe=strategy.timeframe,
            strategy_type=strategy.strategy_type,
            philosophy=strategy.philosophy,
            review_status=review_status,
            metadata_json={
                "market_regime_requirements": strategy.market_regime_requirements,
                "exceptions": strategy.exceptions,
                "ambiguities": strategy.ambiguities,
                "source_references": strategy.source_references,
            },
        )
        session.add(strategy_obj)
        await session.flush()
        logger.info(f"Created strategy: {strategy.name}")

        # Add evidence links for the strategy
        if strategy.chunk_id:
            evidence = StrategyEvidence(
                strategy_id=strategy_obj.id,
                chunk_id=strategy.chunk_id,
            )
            session.add(evidence)

        # Add rules
        for idx, rule in enumerate(strategy.rules):
            rule_obj = StrategyRule(
                strategy_id=strategy_obj.id,
                rule_text=rule.rule_text,
                rule_category=self._map_category(rule.category),
                classification=rule.classification.lower(),
                structured_data={"numeric_definition": rule.numeric_definition}
                if rule.numeric_definition
                else None,
                rule_order=idx,
            )
            session.add(rule_obj)
            await session.flush()

            # Add evidence for the rule
            if rule.chunk_id:
                rule_evidence = RuleEvidence(
                    rule_id=rule_obj.id,
                    chunk_id=rule.chunk_id,
                    excerpt=rule.source_reference,
                )
                session.add(rule_evidence)

        return strategy_obj

    def _map_category(self, category: str) -> str:
        """Map extracted category to RuleCategory enum value."""
        category_lower = category.lower()

        mapping = {
            "technical": RuleCategory.TECHNICAL.value,
            "fundamental": RuleCategory.FUNDAMENTAL.value,
            "market_regime": RuleCategory.MARKET_REGIME.value,
            "setup": RuleCategory.SETUP.value,
            "entry": RuleCategory.ENTRY.value,
            "confirmation": RuleCategory.CONFIRMATION.value,
            "exit": RuleCategory.EXIT.value,
            "stop_loss": RuleCategory.STOP_LOSS.value,
            "risk_management": RuleCategory.RISK_MANAGEMENT.value,
            "position_sizing": RuleCategory.POSITION_SIZING.value,
            "subjective": RuleCategory.SUBJECTIVE.value,
            "exception": RuleCategory.EXCEPTION.value,
        }

        return mapping.get(category_lower, RuleCategory.OTHER.value)

    async def generate_hypotheses_from_strategy(
        self,
        session: AsyncSession,
        strategy: Strategy,
    ) -> list[Hypothesis]:
        """Generate testable hypotheses from a strategy.

        Args:
            session: Database session.
            strategy: The strategy to generate hypotheses from.

        Returns:
            List of created Hypothesis objects.
        """
        hypotheses: list[Hypothesis] = []

        # This would typically use an LLM to generate hypotheses
        # For now, this is a placeholder for future implementation

        # Example: If strategy has objective rules, create hypotheses about them
        objective_rules = [
            r
            for r in strategy.rules
            if r.classification == RuleClassification.OBJECTIVE.value
        ]

        for rule in objective_rules:
            # Create a simple hypothesis template
            hypothesis_text = f"Stocks matching the condition '{rule.rule_text}' will outperform over the following period."

            hypothesis = Hypothesis(
                hypothesis_text=hypothesis_text,
                description=f"Generated from strategy: {strategy.name}",
                variables_required=["close", "volume"],  # Placeholder
                source_strategy_id=strategy.id,
                status="PROPOSED",
            )
            session.add(hypothesis)
            await session.flush()

            # Link to same evidence as the rule
            for rule_evidence in rule.evidence:
                hyp_evidence = HypothesisEvidence(
                    hypothesis_id=hypothesis.id,
                    chunk_id=rule_evidence.chunk_id,
                )
                session.add(hyp_evidence)

            hypotheses.append(hypothesis)
            logger.info(f"Generated hypothesis from rule: {rule.id}")

        return hypotheses
