from datetime import datetime
from enum import Enum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

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


class DocumentType(str, Enum):
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
    document_type: Mapped[DocumentType] = mapped_column(
        String(50), nullable=False, default=DocumentType.OTHER
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
    era: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "1980s-present"
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Trader(id={self.id}, name='{self.name}')>"


class Concept(Base):
    """Represents a trading/investing concept extracted from source material."""

    __tablename__ = "concepts"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="other"
    )  # technical, fundamental, risk_management, market_regime, psychology, other
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PROPOSED"
    )  # PROPOSED, REVIEWED, APPROVED, REJECTED

    # Relationships - many-to-many for related concepts
    related_concepts: Mapped[list["Concept"]] = relationship(
        "Concept",
        secondary="concept_relationships",
        primaryjoin="and_(Concept.id==concept_relationships.c.concept_id)",
        secondaryjoin="and_(Concept.id==concept_relationships.c.related_concept_id)",
    )

    def __repr__(self) -> str:
        return f"<Concept(id={self.id}, name='{self.name}')>"


class ConceptRelationship(Base):
    """Junction table for concept relationships."""

    __tablename__ = "concept_relationships"

    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    related_concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    relationship_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g., "related_to", "broader", "narrower"


class Strategy(Base):
    """Represents a trading strategy extracted from source material."""

    __tablename__ = "strategies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trader_id: Mapped[int | None] = mapped_column(
        ForeignKey("traders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    timeframe: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g., "daily", "weekly", "intraday"
    strategy_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g., "momentum", "breakout", "trend_following"
    philosophy: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PROPOSED"
    )  # PROPOSED, REVIEWED, APPROVED, REJECTED

    # Relationships
    trader: Mapped["Trader | None"] = relationship("Trader")

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name='{self.name}')>"


class RuleClassification(str, Enum):
    """Classification of how well a rule can be formalized."""

    OBJECTIVE = "objective"  # Can be precisely defined numerically
    SUBJECTIVE = "subjective"  # Requires human judgment
    UNRESOLVED = "unresolved"  # Unclear or incomplete in source


class RuleCategory(str, Enum):
    """Category of trading rule."""

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    MARKET_REGIME = "market_regime"
    RISK_MANAGEMENT = "risk_management"
    POSITION_SIZING = "position_sizing"
    ENTRY = "entry"
    EXIT = "exit"
    STOP_LOSS = "stop_loss"
    CONFIRMATION = "confirmation"
    SETUP = "setup"
    OTHER = "other"


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
    numeric_definition: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Precise numeric rule if applicable
    rule_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<StrategyRule(id={self.id}, strategy_id={self.strategy_id})>"


class EvidenceType(str, Enum):
    """Type of evidence link."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    ELABORATES = "elaborates"
    DEFINES = "defines"


class Evidence(Base):
    """Links extracted knowledge to source document chunks (provenance)."""

    __tablename__ = "evidence"

    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EvidenceType.SUPPORTS.value
    )
    quote: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Exact quote from the chunk
    context: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Additional context around the quote

    # Polymorphic relationships - what this evidence supports
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    strategy_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_rules.id", ondelete="CASCADE"), nullable=True, index=True
    )
    concept_id: Mapped[int | None] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Relationships
    chunk: Mapped["DocumentChunk"] = relationship("DocumentChunk")
    strategy: Mapped["Strategy | None"] = relationship("Strategy")
    strategy_rule: Mapped["StrategyRule | None"] = relationship("StrategyRule")
    concept: Mapped["Concept | None"] = relationship("Concept")

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, chunk_id={self.chunk_id})>"


class Hypothesis(Base):
    """Represents a testable hypothesis generated from source material."""

    __tablename__ = "hypotheses"

    hypothesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables_required: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )  # List of required data variables
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PROPOSED"
    )  # PROPOSED, TESTED, VALIDATED, INVALIDATED
    test_results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )  # Results if tested

    def __repr__(self) -> str:
        return f"<Hypothesis(id={self.id})>"
