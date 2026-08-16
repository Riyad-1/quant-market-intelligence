"""Database models for concepts, strategies, rules, and evidence with full provenance tracking."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class ReviewStatus(str, PyEnum):
    """Review status for extracted strategies and concepts."""

    PROPOSED = "PROPOSED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RuleCategory(str, PyEnum):
    """Category of a strategy rule."""

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    MARKET_REGIME = "market_regime"
    SETUP = "setup"
    ENTRY = "entry"
    CONFIRMATION = "confirmation"
    EXIT = "exit"
    STOP_LOSS = "stop_loss"
    RISK_MANAGEMENT = "risk_management"
    POSITION_SIZING = "position_sizing"
    SUBJECTIVE = "subjective"
    EXCEPTION = "exception"
    OTHER = "other"


class RuleClassification(str, PyEnum):
    """Classification of rule certainty."""

    OBJECTIVE = "objective"  # Can be precisely defined numerically
    SUBJECTIVE = "subjective"  # Requires human judgment
    UNRESOLVED = "unresolved"  # Unclear or incomplete in source


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all database models."""

    metadata = metadata

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class DocumentType(str, PyEnum):
    """Types of documents that can be ingested."""

    BOOK = "book"
    RESEARCH_PAPER = "research_paper"
    INTERVIEW = "interview"
    STRATEGY_DOCUMENT = "strategy_document"
    RESEARCH_NOTE = "research_note"
    REPORT = "report"
    OTHER = "other"


class Document(Base):
    """Represents a source document (book, paper, interview, etc.)."""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DocumentType.OTHER.value
    )
    publication_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    sections: Mapped[list["DocumentSection"]] = relationship(
        "DocumentSection",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}')>"


class DocumentSection(Base):
    """Represents a section/chapter within a document."""

    __tablename__ = "document_sections"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=1)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="sections")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="section",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DocumentSection(id={self.id}, heading='{self.heading}')>"


class DocumentChunk(Base):
    """Represents a text chunk from a document section with embedding."""

    __tablename__ = "document_chunks"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    chunk_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document")
    section: Mapped["DocumentSection | None"] = relationship(
        "DocumentSection", back_populates="chunks"
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, chunk_index={self.chunk_index})>"


class Trader(Base):
    """Represents a trader or investor whose methodology appears in source material."""

    __tablename__ = "traders"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    known_for: Mapped[str | None] = mapped_column(String(500), nullable=True)
    era: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    strategies = relationship(
        "Strategy", back_populates="trader", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Trader(id={self.id}, name='{self.name}')>"


class Concept(Base):
    """Represents a trading/investing concept extracted from source material."""

    __tablename__ = "concepts"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="other"
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewStatus.PROPOSED.value
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    evidence = relationship(
        "ConceptEvidence", back_populates="concept", cascade="all, delete-orphan"
    )
    related_as_source = relationship(
        "ConceptRelation",
        foreign_keys="ConceptRelation.source_concept_id",
        back_populates="source_concept",
        cascade="all, delete-orphan",
    )
    related_as_target = relationship(
        "ConceptRelation",
        foreign_keys="ConceptRelation.target_concept_id",
        back_populates="target_concept",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Concept(id={self.id}, name='{self.name}')>"


class ConceptEvidence(Base):
    """Links a concept to supporting document chunks (provenance)."""

    __tablename__ = "concept_evidence"

    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("concept_id", "chunk_id", name="uq_concept_chunk"),
    )

    # Relationships
    concept = relationship("Concept", back_populates="evidence")
    chunk = relationship("DocumentChunk", backref="concept_evidence")

    def __repr__(self) -> str:
        return f"<ConceptEvidence(concept_id={self.concept_id}, chunk_id={self.chunk_id})>"


class ConceptRelation(Base):
    """Represents relationships between concepts."""

    __tablename__ = "concept_relations"

    source_concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_concept_id",
            "target_concept_id",
            "relation_type",
            name="uq_concept_relation",
        ),
    )

    # Relationships
    source_concept = relationship(
        "Concept",
        foreign_keys=[source_concept_id],
        back_populates="related_as_source",
    )
    target_concept = relationship(
        "Concept",
        foreign_keys=[target_concept_id],
        back_populates="related_as_target",
    )

    def __repr__(self) -> str:
        return f"<ConceptRelation({self.relation_type})>"


class Strategy(Base):
    """Represents a trading strategy extracted from source material."""

    __tablename__ = "strategies"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trader_id: Mapped[int | None] = mapped_column(
        ForeignKey("traders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    timeframe: Mapped[str | None] = mapped_column(String(50), nullable=True)
    strategy_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    philosophy: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewStatus.PROPOSED.value
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    trader = relationship("Trader", back_populates="strategies")
    rules = relationship(
        "StrategyRule", back_populates="strategy", cascade="all, delete-orphan"
    )
    evidence = relationship(
        "StrategyEvidence", back_populates="strategy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name='{self.name}')>"


class StrategyRule(Base):
    """Represents an individual rule within a trading strategy."""

    __tablename__ = "strategy_rules"

    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    rule_category: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RuleCategory.OTHER.value
    )
    classification: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RuleClassification.UNRESOLVED.value
    )
    structured_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    rule_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    strategy = relationship("Strategy", back_populates="rules")
    evidence = relationship(
        "RuleEvidence", back_populates="rule", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<StrategyRule(id={self.id}, strategy_id={self.strategy_id})>"


class StrategyEvidence(Base):
    """Links a strategy to supporting document chunks (provenance)."""

    __tablename__ = "strategy_evidence"

    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("strategy_id", "chunk_id", name="uq_strategy_chunk"),
    )

    # Relationships
    strategy = relationship("Strategy", back_populates="evidence")
    chunk = relationship("DocumentChunk", backref="strategy_evidence")

    def __repr__(self) -> str:
        return f"<StrategyEvidence(strategy_id={self.strategy_id}, chunk_id={self.chunk_id})>"


class RuleEvidence(Base):
    """Links a strategy rule to supporting document chunks (provenance)."""

    __tablename__ = "rule_evidence"

    rule_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("rule_id", "chunk_id", name="uq_rule_chunk"),)

    # Relationships
    rule = relationship("StrategyRule", back_populates="evidence")
    chunk = relationship("DocumentChunk", backref="rule_evidence")

    def __repr__(self) -> str:
        return f"<RuleEvidence(rule_id={self.rule_id}, chunk_id={self.chunk_id})>"


class Hypothesis(Base):
    """Represents a testable hypothesis generated from source material."""

    __tablename__ = "hypotheses"

    hypothesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables_required: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    source_strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PROPOSED"
    )
    test_results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    evidence = relationship(
        "HypothesisEvidence", back_populates="hypothesis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Hypothesis(id={self.id})>"


class HypothesisEvidence(Base):
    """Links a hypothesis to supporting document chunks (provenance)."""

    __tablename__ = "hypothesis_evidence"

    hypothesis_id: Mapped[int] = mapped_column(
        ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("hypothesis_id", "chunk_id", name="uq_hypothesis_chunk"),
    )

    # Relationships
    hypothesis = relationship("Hypothesis", back_populates="evidence")
    chunk = relationship("DocumentChunk", backref="hypothesis_evidence")

    def __repr__(self) -> str:
        return f"<HypothesisEvidence(hypothesis_id={self.hypothesis_id}, chunk_id={self.chunk_id})>"
