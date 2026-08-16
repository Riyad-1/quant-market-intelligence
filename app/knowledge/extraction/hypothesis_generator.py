"""Hypothesis generation service for converting strategies into testable hypotheses."""

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Strategy, StrategyRule, Hypothesis, HypothesisEvidence
from app.knowledge.schemas import HypothesisCreate

logger = logging.getLogger(__name__)


@dataclass
class GeneratedHypothesis:
    """A generated testable hypothesis."""

    hypothesis_text: str
    description: str
    variables_required: list[str]
    confidence: float
    ambiguities: list[str] = field(default_factory=list)
    source_rule_ids: list[int] = field(default_factory=list)


@dataclass
class HypothesisGenerationResult:
    """Result of hypothesis generation from a strategy."""

    success: bool
    hypotheses: list[GeneratedHypothesis] = field(default_factory=list)
    error_message: str | None = None


class HypothesisGenerator:
    """Service for generating testable hypotheses from trading strategies.
    
    This service analyzes strategy rules and converts them into clear,
    falsifiable hypotheses that can be tested quantitatively.
    
    Each hypothesis includes:
    - Clear statement of the expected relationship
    - List of required data variables
    - Confidence score based on rule clarity
    - Identified ambiguities that may prevent testing
    - Links to source rules and evidence
    """

    def __init__(self, llm_provider: Any | None = None):
        """Initialize the generator.
        
        Args:
            llm_provider: Optional LLM provider for natural language generation.
                         If not provided, uses template-based generation.
        """
        self.llm_provider = llm_provider

    async def generate_from_strategy(
        self,
        session: AsyncSession,
        strategy_id: int,
    ) -> HypothesisGenerationResult:
        """Generate testable hypotheses from a strategy.
        
        Args:
            session: Database session
            strategy_id: ID of the strategy to analyze
            
        Returns:
            HypothesisGenerationResult with generated hypotheses
            
        Raises:
            ValueError: If strategy doesn't exist
        """
        # Load strategy
        strategy = await self._load_strategy(session, strategy_id)
        if not strategy:
            return HypothesisGenerationResult(
                success=False,
                error_message=f"Strategy {strategy_id} not found",
            )

        # Load rules
        rules = await self._load_strategy_rules(session, strategy_id)
        if not rules:
            return HypothesisGenerationResult(
                success=False,
                error_message="Strategy has no rules to generate hypotheses from",
            )

        # Generate hypotheses
        hypotheses = await self._generate_hypotheses(strategy, rules)

        return HypothesisGenerationResult(
            success=True,
            hypotheses=hypotheses,
        )

    async def save_hypotheses(
        self,
        session: AsyncSession,
        strategy_id: int,
        generated_hypotheses: list[GeneratedHypothesis],
        status: str = "PROPOSED",
    ) -> list[Hypothesis]:
        """Save generated hypotheses to the database.
        
        Args:
            session: Database session
            strategy_id: ID of the source strategy
            generated_hypotheses: List of generated hypotheses
            status: Initial status for hypotheses
            
        Returns:
            List of saved Hypothesis objects
        """
        saved = []
        
        for gen_hyp in generated_hypotheses:
            # Create hypothesis
            hyp = Hypothesis(
                hypothesis_text=gen_hyp.hypothesis_text,
                description=gen_hyp.description,
                variables_required=gen_hyp.variables_required,
                source_strategy_id=strategy_id,
                status=status,
                confidence_score=gen_hyp.confidence,
                metadata_json={
                    "ambiguities": gen_hyp.ambiguities,
                    "source_rule_ids": gen_hyp.source_rule_ids,
                },
            )
            
            session.add(hyp)
            await session.flush()  # Get ID
            
            # Link to source rules as evidence
            for rule_id in gen_hyp.source_rule_ids:
                evidence = HypothesisEvidence(
                    hypothesis_id=hyp.id,
                    rule_id=rule_id,
                )
                session.add(evidence)
            
            saved.append(hyp)
        
        return saved

    async def _load_strategy(
        self, session: AsyncSession, strategy_id: int
    ):
        """Load a strategy by ID."""
        from sqlalchemy import select
        from app.db.models import Strategy
        
        result = await session.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def _load_strategy_rules(
        self, session: AsyncSession, strategy_id: int
    ):
        """Load all rules for a strategy."""
        from sqlalchemy import select
        from app.db.models import StrategyRule
        
        result = await session.execute(
            select(StrategyRule)
            .where(StrategyRule.strategy_id == strategy_id)
            .order_by(StrategyRule.rule_order)
        )
        return list(result.scalars().all())

    async def _generate_hypotheses(
        self,
        strategy: Any,
        rules: list[Any],
    ) -> list[GeneratedHypothesis]:
        """Generate hypotheses from strategy rules.
        
        Groups related rules and converts them into testable statements.
        """
        hypotheses = []
        
        # Group rules by category
        categorized = self._categorize_rules(rules)
        
        # Generate hypothesis for each meaningful category group
        for category, cat_rules in categorized.items():
            if not cat_rules:
                continue
            
            # Skip categories that don't translate well to hypotheses
            if category in ["subjective", "exception"]:
                continue
            
            hyp = self._create_hypothesis_for_category(
                strategy, category, cat_rules
            )
            if hyp:
                hypotheses.append(hyp)
        
        # Also try to create a composite hypothesis from all objective rules
        composite = self._create_composite_hypothesis(strategy, rules)
        if composite:
            hypotheses.append(composite)
        
        return hypotheses

    def _categorize_rules(
        self, rules: list[Any]
    ) -> dict[str, list[Any]]:
        """Group rules by category."""
        grouped: dict[str, list[Any]] = {}
        for rule in rules:
            cat = rule.category or "other"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(rule)
        return grouped

    def _create_hypothesis_for_category(
        self,
        strategy: Any,
        category: str,
        rules: list[Any],
    ) -> GeneratedHypothesis | None:
        """Create a hypothesis from rules in a specific category."""
        # Extract variables and conditions from rules
        variables = []
        conditions = []
        ambiguities = []
        
        for rule in rules:
            rule_data = rule.rule_data or {}
            
            # Extract metric/variable
            metric = rule_data.get("metric", "")
            if metric:
                variables.append(metric)
            
            # Extract condition
            operator = rule_data.get("operator", "")
            value = rule_data.get("value")
            
            if metric and operator:
                if value is not None:
                    conditions.append(f"{metric} {operator} {value}")
                else:
                    conditions.append(f"{metric} {operator} [threshold]")
            
            # Check for subjectivity
            if rule.classification == "SUBJECTIVE":
                ambiguities.append(f"Rule '{rule.rule_text}' contains subjective elements")
            elif rule.classification == "UNRESOLVED":
                ambiguities.append(f"Rule '{rule.rule_text}' is ambiguous")
        
        if not conditions:
            return None
        
        # Build hypothesis text
        category_name = category.replace("_", " ")
        condition_str = " and ".join(conditions[:3])  # Limit complexity
        if len(conditions) > 3:
            condition_str += f" and {len(conditions) - 3} other {category_name} conditions"
        
        hypothesis_text = (
            f"Stocks {condition_str} will outperform over the following "
            f"{strategy.timeframe or 'medium'} term."
        )
        
        description = (
            f"This hypothesis tests whether {category_name} criteria from the "
            f"'{strategy.name}' strategy predict positive returns. "
            f"Based on {len(rules)} rule(s)."
        )
        
        # Calculate confidence
        confidence = 0.9 - (len(ambiguities) * 0.15)
        confidence = max(0.3, min(0.95, confidence))
        
        return GeneratedHypothesis(
            hypothesis_text=hypothesis_text,
            description=description,
            variables_required=list(set(variables)),
            confidence=round(confidence, 2),
            ambiguities=ambiguities,
            source_rule_ids=[r.id for r in rules],
        )

    def _create_composite_hypothesis(
        self,
        strategy: Any,
        rules: list[Any],
    ) -> GeneratedHypothesis | None:
        """Create a composite hypothesis from all objective rules."""
        # Filter to objective rules only
        objective_rules = [
            r for r in rules 
            if r.classification != "SUBJECTIVE" and r.classification != "UNRESOLVED"
        ]
        
        if len(objective_rules) < 2:
            return None  # Need at least 2 rules for composite
        
        variables = set()
        rule_count = len(objective_rules)
        
        for rule in objective_rules:
            rule_data = rule.rule_data or {}
            metric = rule_data.get("metric", "")
            if metric:
                variables.add(metric)
        
        hypothesis_text = (
            f"A portfolio of stocks meeting all {rule_count} objective criteria "
            f"from the '{strategy.name}' strategy will generate positive "
            f"risk-adjusted returns over the {strategy.timeframe or 'investment'} horizon."
        )
        
        description = (
            f"Composite hypothesis testing the full rule set of '{strategy.name}'. "
            f"Includes {rule_count} objective rules across multiple categories. "
            f"Excludes subjective or ambiguous conditions."
        )
        
        return GeneratedHypothesis(
            hypothesis_text=hypothesis_text,
            description=description,
            variables_required=list(variables),
            confidence=0.75,  # Moderate confidence for composite
            ambiguities=[],
            source_rule_ids=[r.id for r in objective_rules],
        )
