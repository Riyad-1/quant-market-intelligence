"""Initial migration - create documents, document_sections, document_chunks tables.

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum type for document_type
    document_type = sa.Enum(
        'BOOK', 'RESEARCH_PAPER', 'INTERVIEW', 'STRATEGY_DOCUMENT',
        'RESEARCH_NOTE', 'REPORT', 'OTHER',
        name='documenttype'
    )
    document_type.create(op.get_bind())

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('author', sa.String(length=200), nullable=True),
        sa.Column('document_type', document_type, nullable=False, default='OTHER'),
        sa.Column('publication_date', sa.String(length=50), nullable=True),
        sa.Column('filename', sa.String(length=500), nullable=True),
        sa.Column('hash', sa.String(length=64), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_documents_hash'), 'documents', ['hash'], unique=False)

    # Create document_sections table
    op.create_table(
        'document_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('heading', sa.String(length=500), nullable=True),
        sa.Column('hierarchy_level', sa.Integer(), nullable=False, default=1),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_sections_document_id'), 'document_sections', ['document_id'], unique=False)

    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('embedding', Vector(dimensions=1536), nullable=True),
        sa.Column('chunk_hash', sa.String(length=64), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['document_sections.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_section_id'), 'document_chunks', ['section_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_chunk_hash'), 'document_chunks', ['chunk_hash'], unique=False)


def downgrade() -> None:
    op.drop_table('document_chunks')
    op.drop_table('document_sections')
    op.drop_table('documents')
    
    # Drop enum type
    document_type = sa.Enum(name='documenttype')
    document_type.drop(op.get_bind())
