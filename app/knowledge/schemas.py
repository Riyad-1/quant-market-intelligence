"""Pydantic schemas for knowledge entities (concepts, strategies, rules, hypotheses)."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============== TRADER SCHEMAS ==============


class TraderBase(BaseModel):
    """Base schema for trader/investor."""

    name: str = Field(..., description="Name of the trader or investor")
    bio: Optional[str] = Field(None, description="Biographical information")
    known_for: Optional[str] = Field(None, description="What they are known for")
    era: Optional[str] = Field(None, description="Time period, e.g., '1980s-present'")
    metadata_json: Optional[dict[str, Any]] = Field(
        None, description="Additional metadata"
    )


class TraderCreate(TraderBase):
    """Schema for creating a trader."""

    pass


class TraderUpdate(BaseModel):
    """Schema for updating a trader."""

    name: Optional[str] = None
    bio: Optional[str] = None
    known_for: Optional[str] = None
    era: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class TraderResponse(TraderBase):
    """Schema for trader response."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ============== CONCEPT SCHEMAS ==============


class ConceptBase(BaseModel):
    """Base schema for trading concept."""

    name: str = Field(..., description="Name of the concept")
    description: Optional[str] = Field(None, description="Description of the concept")
    category: str = Field(default="other", description="Category of the concept")
    review_status: str = Field(
        default="PROPOSED", description="Review status: PROPOSED, REVIEWED, APPROVED, REJECTED"
    )
    metadata_json: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class ConceptCreate(ConceptBase):
    """Schema for creating a concept."""

    pass


class ConceptUpdate(BaseModel):
    """Schema for updating a concept."""

    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    review_status: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class ConceptEvidenceBase(BaseModel):
    """Base schema for concept evidence."""

    chunk_id: int
    relevance_score: Optional[float] = None
    excerpt: Optional[str] = None


class ConceptEvidenceCreate(ConceptEvidenceBase):
    """Schema for creating concept evidence."""

    concept_id: int


class ConceptEvidenceResponse(ConceptEvidenceBase):
    """Schema for concept evidence response."""

    id: int
    concept_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConceptRelationBase(BaseModel):
    """Base schema for concept relations."""

    source_concept_id: int
    target_concept_id: int
    relation_type: str  # e.g., "RELATED_TO", "BROADER_THAN", "NARROWER_THAN"


class ConceptRelationCreate(ConceptRelationBase):
    """Schema for creating a concept relation."""

    pass


class ConceptRelationResponse(ConceptRelationBase):
    """Schema for concept relation response."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConceptResponse(ConceptBase):
    """Schema for concept response with relationships."""

    id: int
    created_at: datetime
    updated_at: datetime
    evidence: list[ConceptEvidenceResponse] = []
    related_concepts: list[ConceptRelationResponse] = []

    model_config = {"from_attributes": True}


# ============== STRATEGY SCHEMAS ==============


class StrategyRuleBase(BaseModel):
    """Base schema for strategy rule."""

    rule_text: str = Field(..., description="Natural language description of the rule")
    rule_category: str = Field(
        default="other",
        description="Category: technical, fundamental, market_regime, setup, entry, confirmation, exit, stop_loss, risk_management, position_sizing, subjective, exception, other",
    )
    classification: str = Field(
        default="unresolved",
        description="Classification: objective, subjective, unresolved",
    )
    structured_data: Optional[dict[str, Any]] = Field(
        None, description="Structured representation for potential execution"
    )
    rule_order: Optional[int] = Field(None, description="Order index for sequencing rules")


class StrategyRuleCreate(StrategyRuleBase):
    """Schema for creating a strategy rule."""

    strategy_id: int


class RuleEvidenceBase(BaseModel):
    """Base schema for rule evidence."""

    chunk_id: int
    relevance_score: Optional[float] = None
    excerpt: Optional[str] = None


class RuleEvidenceCreate(RuleEvidenceBase):
    """Schema for creating rule evidence."""

    rule_id: int


class RuleEvidenceResponse(RuleEvidenceBase):
    """Schema for rule evidence response."""

    id: int
    rule_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyRuleResponse(StrategyRuleBase):
    """Schema for strategy rule response."""

    id: int
    strategy_id: int
    created_at: datetime
    evidence: list[RuleEvidenceResponse] = []

    model_config = {"from_attributes": True}


class StrategyBase(BaseModel):
    """Base schema for trading strategy."""

    name: str = Field(..., description="Name of the strategy")
    description: Optional[str] = Field(None, description="Description of the strategy")
    trader_id: Optional[int] = Field(None, description="ID of associated trader")
    timeframe: Optional[str] = Field(None, description="Timeframe: daily, weekly, intraday, etc.")
    strategy_type: Optional[str] = Field(
        None, description="Type: momentum, breakout, trend_following, etc."
    )
    philosophy: Optional[str] = Field(None, description="Philosophical foundation")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    review_status: str = Field(
        default="PROPOSED", description="Review status: PROPOSED, REVIEWED, APPROVED, REJECTED"
    )
    metadata_json: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class StrategyCreate(StrategyBase):
    """Schema for creating a strategy."""

    pass


class StrategyUpdate(BaseModel):
    """Schema for updating a strategy."""

    name: Optional[str] = None
    description: Optional[str] = None
    trader_id: Optional[int] = None
    timeframe: Optional[str] = None
    strategy_type: Optional[str] = None
    philosophy: Optional[str] = None
    confidence: Optional[float] = None
    review_status: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class StrategyEvidenceBase(BaseModel):
    """Base schema for strategy evidence."""

    chunk_id: int
    relevance_score: Optional[float] = None
    excerpt: Optional[str] = None


class StrategyEvidenceCreate(StrategyEvidenceBase):
    """Schema for creating strategy evidence."""

    strategy_id: int


class StrategyEvidenceResponse(StrategyEvidenceBase):
    """Schema for strategy evidence response."""

    id: int
    strategy_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyResponse(StrategyBase):
    """Schema for strategy response with relationships."""

    id: int
    trader_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    rules: list[StrategyRuleResponse] = []
    evidence: list[StrategyEvidenceResponse] = []
    trader: Optional[TraderResponse] = None

    model_config = {"from_attributes": True}


# ============== HYPOTHESIS SCHEMAS ==============


class HypothesisEvidenceBase(BaseModel):
    """Base schema for hypothesis evidence."""

    chunk_id: int
    relevance_score: Optional[float] = None
    excerpt: Optional[str] = None


class HypothesisEvidenceCreate(HypothesisEvidenceBase):
    """Schema for creating hypothesis evidence."""

    hypothesis_id: int


class HypothesisEvidenceResponse(HypothesisEvidenceBase):
    """Schema for hypothesis evidence response."""

    id: int
    hypothesis_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HypothesisBase(BaseModel):
    """Base schema for testable hypothesis."""

    hypothesis_text: str = Field(..., description="The hypothesis statement")
    description: Optional[str] = Field(None, description="Additional description")
    variables_required: Optional[list[str]] = Field(
        None, description="List of required data variables for testing"
    )
    source_strategy_id: Optional[int] = Field(
        None, description="ID of source strategy if applicable"
    )
    status: str = Field(
        default="PROPOSED",
        description="Status: PROPOSED, TESTED, VALIDATED, INVALIDATED",
    )
    test_results: Optional[dict[str, Any]] = Field(None, description="Test results if available")


class HypothesisCreate(HypothesisBase):
    """Schema for creating a hypothesis."""

    pass


class HypothesisUpdate(BaseModel):
    """Schema for updating a hypothesis."""

    hypothesis_text: Optional[str] = None
    description: Optional[str] = None
    variables_required: Optional[list[str]] = None
    source_strategy_id: Optional[int] = None
    status: Optional[str] = None
    test_results: Optional[dict[str, Any]] = None


class HypothesisResponse(HypothesisBase):
    """Schema for hypothesis response with relationships."""

    id: int
    created_at: datetime
    evidence: list[HypothesisEvidenceResponse] = []

    model_config = {"from_attributes": True}


# ============== DOCUMENT CHUNK REFERENCES ==============


class DocumentChunkReference(BaseModel):
    """Reference to a document chunk for provenance."""

    id: int
    document_id: int
    section_id: Optional[int] = None
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    chunk_index: int

    model_config = {"from_attributes": True}


class DocumentReference(BaseModel):
    """Reference to a document for provenance."""

    id: int
    title: str
    author: Optional[str] = None
    document_type: str

    model_config = {"from_attributes": True}


# ============== COMPREHENSIVE RESPONSES WITH FULL PROVENANCE ==============


class ConceptWithProvenance(ConceptResponse):
    """Concept with full provenance chain."""

    evidence_with_chunks: list[dict[str, Any]] = []


class StrategyWithProvenance(StrategyResponse):
    """Strategy with full provenance chain."""

    evidence_with_chunks: list[dict[str, Any]] = []
    rules_with_evidence: list[dict[str, Any]] = []


class HypothesisWithProvenance(HypothesisResponse):
    """Hypothesis with full provenance chain."""

    evidence_with_chunks: list[dict[str, Any]] = []


# ============================================================================
# Strategy Comparison (Phase 8)
# ============================================================================


class SharedPrinciple(BaseModel):
    """A principle shared between two strategies."""

    description: str
    strategy_a_rule_ids: list[int]
    strategy_b_rule_ids: list[int]
    confidence: float
    source_count: int


class RuleConflict(BaseModel):
    """A conflict between rules in two strategies."""

    description: str
    strategy_a_rule_id: int
    strategy_a_rule_text: str
    strategy_b_rule_id: int
    strategy_b_rule_text: str
    conflict_type: str  # e.g., "contradictory_operators", "different_thresholds"


class UniqueRule(BaseModel):
    """A rule unique to one strategy."""

    rule_id: int
    rule_text: str
    category: str | None
    classification: str | None


class MetadataComparison(BaseModel):
    """Comparison of strategy metadata."""

    timeframe_match: bool
    market_regime_match: bool
    risk_management_similar: bool
    notes: str


class StrategyComparison(BaseModel):
    """Result of comparing two strategies."""

    strategy_a_id: int
    strategy_b_id: int
    similarity_score: float  # 0.0 to 1.0
    
    shared_principles: list[SharedPrinciple] = []
    conflicts: list[RuleConflict] = []
    
    unique_to_strategy_a: list[UniqueRule] = []
    unique_to_strategy_b: list[UniqueRule] = []
    
    metadata_comparison: MetadataComparison | None = None
    summary: str = ""


class StrategyComparisonRequest(BaseModel):
    """Request to compare two strategies."""

    strategy_a_id: int
    strategy_b_id: int
    include_metadata: bool = True
    min_confidence: float = 0.5
