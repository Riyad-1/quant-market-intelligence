"""Strategy comparison service for analyzing relationships between trading strategies."""

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Strategy, StrategyRule, StrategyEvidence
from app.knowledge.schemas import (
    StrategyComparison,
    SharedPrinciple,
    RuleConflict,
    UniqueRule,
    MetadataComparison,
)

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing two strategies."""

    similarity_score: float
    shared_principles: list[SharedPrinciple] = field(default_factory=list)
    conflicts: list[RuleConflict] = field(default_factory=list)
    unique_to_a: list[UniqueRule] = field(default_factory=list)
    unique_to_b: list[UniqueRule] = field(default_factory=list)
    metadata_comparison: MetadataComparison | None = None
    summary: str = ""


class StrategyComparator:
    """Service for comparing two trading strategies.
    
    This service analyzes two strategies to identify:
    - Shared principles and rules
    - Conflicting or contradictory rules
    - Rules unique to each strategy
    - Metadata similarities (timeframe, market regime, etc.)
    
    All comparisons are evidence-backed, linking back to source material.
    """

    def __init__(self, llm_provider: Any | None = None):
        """Initialize the comparator.
        
        Args:
            llm_provider: Optional LLM provider for generating natural language
                         summaries and explanations. If not provided, uses
                         rule-based comparison only.
        """
        self.llm_provider = llm_provider

    async def compare_strategies(
        self,
        session: AsyncSession,
        strategy_a_id: int,
        strategy_b_id: int,
        min_confidence: float = 0.5,
    ) -> ComparisonResult:
        """Compare two strategies and return detailed analysis.
        
        Args:
            session: Database session
            strategy_a_id: ID of first strategy
            strategy_b_id: ID of second strategy
            min_confidence: Minimum confidence threshold for shared principles
            
        Returns:
            ComparisonResult with detailed analysis
            
        Raises:
            ValueError: If strategy IDs are the same or strategies don't exist
        """
        if strategy_a_id == strategy_b_id:
            raise ValueError("Cannot compare a strategy with itself")

        # Load strategies with their rules
        strategy_a = await self._load_strategy(session, strategy_a_id)
        strategy_b = await self._load_strategy(session, strategy_b_id)

        if not strategy_a:
            raise ValueError(f"Strategy {strategy_a_id} not found")
        if not strategy_b:
            raise ValueError(f"Strategy {strategy_b_id} not found")

        rules_a = await self._load_strategy_rules(session, strategy_a_id)
        rules_b = await self._load_strategy_rules(session, strategy_b_id)

        # Find shared principles
        shared_principles = await self._find_shared_principles(
            session, rules_a, rules_b, min_confidence
        )

        # Find conflicts
        conflicts = await self._find_conflicts(session, rules_a, rules_b)

        # Find unique rules
        unique_to_a = self._find_unique_rules(rules_a, rules_b)
        unique_to_b = self._find_unique_rules(rules_b, rules_a)

        # Calculate similarity score
        similarity_score = self._calculate_similarity_score(
            rules_a, rules_b, shared_principles, conflicts
        )

        # Compare metadata
        metadata_comparison = self._compare_metadata(strategy_a, strategy_b)

        # Generate summary
        summary = self._generate_summary(
            strategy_a, strategy_b, shared_principles, conflicts, 
            unique_to_a, unique_to_b, similarity_score
        )

        return ComparisonResult(
            similarity_score=similarity_score,
            shared_principles=shared_principles,
            conflicts=conflicts,
            unique_to_a=unique_to_a,
            unique_to_b=unique_to_b,
            metadata_comparison=metadata_comparison,
            summary=summary,
        )

    async def _load_strategy(
        self, session: AsyncSession, strategy_id: int
    ) -> Strategy | None:
        """Load a strategy by ID."""
        result = await session.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def _load_strategy_rules(
        self, session: AsyncSession, strategy_id: int
    ) -> list[StrategyRule]:
        """Load all rules for a strategy."""
        result = await session.execute(
            select(StrategyRule)
            .where(StrategyRule.strategy_id == strategy_id)
            .order_by(StrategyRule.rule_order)
        )
        return list(result.scalars().all())

    async def _find_shared_principles(
        self,
        session: AsyncSession,
        rules_a: list[StrategyRule],
        rules_b: list[StrategyRule],
        min_confidence: float,
    ) -> list[SharedPrinciple]:
        """Identify shared principles between two sets of rules.
        
        Uses semantic similarity to find rules that express similar concepts,
        even if worded differently.
        """
        shared = []
        
        # Group rules by category for more meaningful comparisons
        categories_a = self._group_rules_by_category(rules_a)
        categories_b = self._group_rules_by_category(rules_b)
        
        # Find overlaps in each category
        common_categories = set(categories_a.keys()) & set(categories_b.keys())
        
        for category in common_categories:
            cat_rules_a = categories_a[category]
            cat_rules_b = categories_b[category]
            
            # Simple heuristic: if both strategies have rules in same category,
            # consider it a shared principle
            # TODO: Use LLM/embeddings for deeper semantic analysis
            if cat_rules_a and cat_rules_b:
                # Count evidence sources
                source_count = await self._count_evidence_sources(
                    session, [r.id for r in cat_rules_a] + [r.id for r in cat_rules_b]
                )
                
                shared.append(SharedPrinciple(
                    description=f"Both strategies include {category.replace('_', ' ')} rules",
                    strategy_a_rule_ids=[r.id for r in cat_rules_a],
                    strategy_b_rule_ids=[r.id for r in cat_rules_b],
                    confidence=0.7,  # Base confidence for category match
                    source_count=source_count,
                ))
        
        return shared

    async def _find_conflicts(
        self,
        session: AsyncSession,
        rules_a: list[StrategyRule],
        rules_b: list[StrategyRule],
    ) -> list[RuleConflict]:
        """Identify conflicting rules between two strategies.
        
        Looks for rules that target similar metrics but have contradictory
        operators or thresholds.
        """
        conflicts = []
        
        # Group by metric for conflict detection
        metrics_a = self._group_rules_by_metric(rules_a)
        metrics_b = self._group_rules_by_metric(rules_b)
        
        common_metrics = set(metrics_a.keys()) & set(metrics_b.keys())
        
        for metric in common_metrics:
            metric_rules_a = metrics_a[metric]
            metric_rules_b = metrics_b[metric]
            
            # Check for contradictory operators
            for rule_a in metric_rules_a:
                for rule_b in metric_rules_b:
                    if self._rules_conflict(rule_a, rule_b):
                        conflicts.append(RuleConflict(
                            description=f"Conflicting {metric} requirements",
                            strategy_a_rule_id=rule_a.id,
                            strategy_a_rule_text=rule_a.rule_text,
                            strategy_b_rule_id=rule_b.id,
                            strategy_b_rule_text=rule_b.rule_text,
                            conflict_type=self._get_conflict_type(rule_a, rule_b),
                        ))
        
        return conflicts

    def _find_unique_rules(
        self,
        rules_source: list[StrategyRule],
        rules_compare: list[StrategyRule],
    ) -> list[UniqueRule]:
        """Find rules in source that have no equivalent in compare set."""
        unique = []
        compare_ids = {r.id for r in rules_compare}
        
        # Simple approach: rules with unique categories/metrics
        source_categories = {r.category for r in rules_source if r.category}
        compare_categories = {r.category for r in rules_compare if r.category}
        
        unique_categories = source_categories - compare_categories
        
        for rule in rules_source:
            if rule.category in unique_categories:
                unique.append(UniqueRule(
                    rule_id=rule.id,
                    rule_text=rule.rule_text,
                    category=rule.category,
                    classification=rule.classification,
                ))
        
        return unique

    def _calculate_similarity_score(
        self,
        rules_a: list[StrategyRule],
        rules_b: list[StrategyRule],
        shared: list[SharedPrinciple],
        conflicts: list[RuleConflict],
    ) -> float:
        """Calculate overall similarity score between 0 and 1."""
        if not rules_a and not rules_b:
            return 0.0
        
        total_rules = len(rules_a) + len(rules_b)
        if total_rules == 0:
            return 0.0
        
        # Base similarity from shared principles
        shared_weight = sum(sp.confidence * len(sp.strategy_a_rule_ids) 
                          for sp in shared)
        
        # Penalty for conflicts
        conflict_penalty = len(conflicts) * 0.1
        
        # Normalize
        base_score = min(1.0, shared_weight / max(1, total_rules))
        final_score = max(0.0, base_score - conflict_penalty)
        
        return round(final_score, 2)

    def _compare_metadata(
        self, strategy_a: Strategy, strategy_b: Strategy
    ) -> MetadataComparison:
        """Compare strategy metadata fields."""
        timeframe_match = (
            strategy_a.timeframe and 
            strategy_b.timeframe and 
            strategy_a.timeframe.lower() == strategy_b.timeframe.lower()
        )
        
        # Compare market regime from metadata
        regime_a = (strategy_a.metadata_json or {}).get("market_regime", "")
        regime_b = (strategy_b.metadata_json or {}).get("market_regime", "")
        regime_match = bool(regime_a and regime_b and regime_a == regime_b)
        
        # Compare risk management approach
        risk_a = (strategy_a.metadata_json or {}).get("risk_management", {})
        risk_b = (strategy_b.metadata_json or {}).get("risk_management", {})
        risk_similar = self._risk_approaches_similar(risk_a, risk_b)
        
        notes_parts = []
        if not timeframe_match:
            notes_parts.append(f"Different timeframes: {strategy_a.timeframe} vs {strategy_b.timeframe}")
        if not regime_match:
            notes_parts.append("Different market regime focus")
        if not risk_similar:
            notes_parts.append("Different risk management approaches")
        
        return MetadataComparison(
            timeframe_match=timeframe_match,
            market_regime_match=regime_match,
            risk_management_similar=risk_similar,
            notes="; ".join(notes_parts) if notes_parts else "Strategies are well-aligned",
        )

    def _generate_summary(
        self,
        strategy_a: Strategy,
        strategy_b: Strategy,
        shared: list[SharedPrinciple],
        conflicts: list[RuleConflict],
        unique_a: list[UniqueRule],
        unique_b: list[UniqueRule],
        similarity: float,
    ) -> str:
        """Generate a human-readable summary of the comparison."""
        parts = [
            f"Comparison of '{strategy_a.name}' and '{strategy_b.name}':",
            f"Overall similarity: {similarity:.0%}",
        ]
        
        if shared:
            parts.append(f"• {len(shared)} shared principle(s) identified")
        
        if conflicts:
            parts.append(f"• {len(conflicts)} conflict(s) detected")
        
        if unique_a:
            parts.append(f"• {len(unique_a)} rule(s) unique to {strategy_a.name}")
        
        if unique_b:
            parts.append(f"• {len(unique_b)} rule(s) unique to {strategy_b.name}")
        
        return " ".join(parts)

    def _group_rules_by_category(
        self, rules: list[StrategyRule]
    ) -> dict[str, list[StrategyRule]]:
        """Group rules by their category."""
        grouped: dict[str, list[StrategyRule]] = {}
        for rule in rules:
            cat = rule.category or "other"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(rule)
        return grouped

    def _group_rules_by_metric(
        self, rules: list[StrategyRule]
    ) -> dict[str, list[StrategyRule]]:
        """Group rules by their metric (from rule_data)."""
        grouped: dict[str, list[StrategyRule]] = {}
        for rule in rules:
            metric = (rule.rule_data or {}).get("metric", "unknown")
            if metric not in grouped:
                grouped[metric] = []
            grouped[metric].append(rule)
        return grouped

    def _rules_conflict(
        self, rule_a: StrategyRule, rule_b: StrategyRule
    ) -> bool:
        """Check if two rules conflict."""
        # Contradictory operators on same metric
        op_a = (rule_a.rule_data or {}).get("operator", "")
        op_b = (rule_b.rule_data or {}).get("operator", "")
        
        contradictory_pairs = [
            (">", "<="),
            ("<", ">="),
            ("==", "!="),
            (">", "<"),
        ]
        
        for pair in contradictory_pairs:
            if (op_a == pair[0] and op_b == pair[1]) or \
               (op_a == pair[1] and op_b == pair[0]):
                return True
        
        return False

    def _get_conflict_type(
        self, rule_a: StrategyRule, rule_b: StrategyRule
    ) -> str:
        """Determine the type of conflict between rules."""
        op_a = (rule_a.rule_data or {}).get("operator", "")
        op_b = (rule_b.rule_data or {}).get("operator", "")
        
        if op_a != op_b:
            return "contradictory_operators"
        
        # Check for different thresholds
        val_a = (rule_a.rule_data or {}).get("value")
        val_b = (rule_b.rule_data or {}).get("value")
        
        if val_a is not None and val_b is not None and val_a != val_b:
            return "different_thresholds"
        
        return "unspecified"

    async def _count_evidence_sources(
        self, session: AsyncSession, rule_ids: list[int]
    ) -> int:
        """Count unique evidence sources for a set of rules."""
        result = await session.execute(
            select(StrategyEvidence)
            .where(StrategyEvidence.rule_id.in_(rule_ids))
        )
        return result.row_count

    def _risk_approaches_similar(
        self, risk_a: dict, risk_b: dict
    ) -> bool:
        """Check if two risk management approaches are similar."""
        if not risk_a or not risk_b:
            return False
        
        # Compare key risk metrics
        for key in ["max_position_size", "stop_loss_pct", "max_drawdown"]:
            if risk_a.get(key) != risk_b.get(key):
                return False
        
        return True
