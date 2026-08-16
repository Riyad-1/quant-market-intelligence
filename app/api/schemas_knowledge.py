"""Pydantic schemas for research and knowledge APIs."""

from pydantic import BaseModel, Field


class ResearchQuery(BaseModel):
    """Schema for research query request."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The research question to answer",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of source documents to retrieve",
    )


class SourceReference(BaseModel):
    """Schema for a source reference in research answers."""

    index: int
    chunk_id: int
    document_id: int
    document_title: str
    document_author: str | None
    page_start: int | None
    page_end: int | None
    section_heading: str | None
    score: float


class ResearchAnswerSchema(BaseModel):
    """Schema for research answer response."""

    answer: str
    sources: list[SourceReference]
    confidence: float = Field(ge=0.0, le=1.0)
    has_sufficient_evidence: bool
    contradictions_identified: bool = False
    ambiguities_identified: bool = False


class ConceptSchema(BaseModel):
    """Schema for a trading concept."""

    id: int | None = None
    name: str
    description: str | None = None
    category: str
    review_status: str = "PROPOSED"
    related_concepts: list[str] = Field(default_factory=list)


class StrategyRuleSchema(BaseModel):
    """Schema for a strategy rule."""

    id: int | None = None
    strategy_id: int | None = None
    rule_text: str
    rule_category: str
    classification: str  # objective, subjective, unresolved
    numeric_definition: str | None = None
    rule_order: int | None = None


class StrategySchema(BaseModel):
    """Schema for a trading strategy."""

    id: int | None = None
    name: str
    description: str | None = None
    trader_id: int | None = None
    trader_name: str | None = None
    timeframe: str | None = None
    strategy_type: str | None = None
    philosophy: str | None = None
    confidence: float | None = None
    review_status: str = "PROPOSED"
    rules: list[StrategyRuleSchema] = Field(default_factory=list)


class EvidenceSchema(BaseModel):
    """Schema for evidence/provenance link."""

    id: int | None = None
    chunk_id: int
    evidence_type: str  # supports, contradicts, elaborates, defines
    quote: str | None = None
    context: str | None = None
    # Linked entity (one of these will be set)
    strategy_id: int | None = None
    strategy_rule_id: int | None = None
    concept_id: int | None = None
    # Source document info
    document_title: str | None = None
    document_author: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class HypothesisSchema(BaseModel):
    """Schema for a testable hypothesis."""

    id: int | None = None
    hypothesis_text: str
    description: str | None = None
    variables_required: list[str] | None = None
    status: str = "PROPOSED"
    test_results: dict | None = None
    source_evidence: list[EvidenceSchema] = Field(default_factory=list)


class TraderSchema(BaseModel):
    """Schema for a trader/investor."""

    id: int | None = None
    name: str
    bio: str | None = None
    known_for: str | None = None
    era: str | None = None
