"""Add knowledge models: traders, concepts, strategies, rules, hypotheses with evidence tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    review_status = postgresql.ENUM(
        'PROPOSED', 'REVIEWED', 'APPROVED', 'REJECTED',
        name='reviewstatus',
        create_type=True
    )
    review_status.create(op.get_bind(), checkfirst=True)

    rule_category = postgresql.ENUM(
        'technical', 'fundamental', 'market_regime', 'setup', 'entry',
        'confirmation', 'exit', 'stop_loss', 'risk_management', 'position_sizing',
        'subjective', 'exception', 'other',
        name='rulecategory',
        create_type=True
    )
    rule_category.create(op.get_bind(), checkfirst=True)

    rule_classification = postgresql.ENUM(
        'objective', 'subjective', 'unresolved',
        name='ruleclassification',
        create_type=True
    )
    rule_classification.create(op.get_bind(), checkfirst=True)

    # Create traders table
    op.create_table(
        'traders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('known_for', sa.String(length=500), nullable=True),
        sa.Column('era', sa.String(length=100), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_traders_name', 'traders', ['name'], unique=True)

    # Create concepts table
    op.create_table(
        'concepts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, default='other'),
        sa.Column('review_status', sa.String(length=20), nullable=False, default='PROPOSED'),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_concepts_name', 'concepts', ['name'])

    # Create concept_evidence table
    op.create_table(
        'concept_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('concept_id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('concept_id', 'chunk_id', name='uq_concept_chunk')
    )
    op.create_index('ix_concept_evidence_concept_id', 'concept_evidence', ['concept_id'])
    op.create_index('ix_concept_evidence_chunk_id', 'concept_evidence', ['chunk_id'])

    # Create concept_relations table
    op.create_table(
        'concept_relations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_concept_id', sa.Integer(), nullable=False),
        sa.Column('target_concept_id', sa.Integer(), nullable=False),
        sa.Column('relation_type', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['source_concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_concept_id', 'target_concept_id', 'relation_type', name='uq_concept_relation')
    )
    op.create_index('ix_concept_relations_source', 'concept_relations', ['source_concept_id'])
    op.create_index('ix_concept_relations_target', 'concept_relations', ['target_concept_id'])

    # Create strategies table
    op.create_table(
        'strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trader_id', sa.Integer(), nullable=True),
        sa.Column('timeframe', sa.String(length=50), nullable=True),
        sa.Column('strategy_type', sa.String(length=50), nullable=True),
        sa.Column('philosophy', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('review_status', sa.String(length=20), nullable=False, default='PROPOSED'),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(['trader_id'], ['traders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategies_name', 'strategies', ['name'])
    op.create_index('ix_strategies_trader_id', 'strategies', ['trader_id'])

    # Create strategy_rules table
    op.create_table(
        'strategy_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('rule_text', sa.Text(), nullable=False),
        sa.Column('rule_category', sa.String(length=50), nullable=False),
        sa.Column('classification', sa.String(length=20), nullable=False),
        sa.Column('structured_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rule_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategy_rules_strategy_id', 'strategy_rules', ['strategy_id'])

    # Create strategy_evidence table
    op.create_table(
        'strategy_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_id', 'chunk_id', name='uq_strategy_chunk')
    )
    op.create_index('ix_strategy_evidence_strategy_id', 'strategy_evidence', ['strategy_id'])
    op.create_index('ix_strategy_evidence_chunk_id', 'strategy_evidence', ['chunk_id'])

    # Create rule_evidence table
    op.create_table(
        'rule_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['strategy_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_id', 'chunk_id', name='uq_rule_chunk')
    )
    op.create_index('ix_rule_evidence_rule_id', 'rule_evidence', ['rule_id'])
    op.create_index('ix_rule_evidence_chunk_id', 'rule_evidence', ['chunk_id'])

    # Create hypotheses table
    op.create_table(
        'hypotheses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hypothesis_text', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('variables_required', sa.JSON(), nullable=True),
        sa.Column('source_strategy_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='PROPOSED'),
        sa.Column('test_results', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(['source_strategy_id'], ['strategies.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_hypotheses_source_strategy_id', 'hypotheses', ['source_strategy_id'])

    # Create hypothesis_evidence table
    op.create_table(
        'hypothesis_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hypothesis_id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['hypothesis_id'], ['hypotheses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hypothesis_id', 'chunk_id', name='uq_hypothesis_chunk')
    )
    op.create_index('ix_hypothesis_evidence_hypothesis_id', 'hypothesis_evidence', ['hypothesis_id'])
    op.create_index('ix_hypothesis_evidence_chunk_id', 'hypothesis_evidence', ['chunk_id'])


def downgrade() -> None:
    op.drop_table('hypothesis_evidence')
    op.drop_table('hypotheses')
    op.drop_table('rule_evidence')
    op.drop_table('strategy_evidence')
    op.drop_table('strategy_rules')
    op.drop_table('strategies')
    op.drop_table('concept_relations')
    op.drop_table('concept_evidence')
    op.drop_table('concepts')
    op.drop_table('traders')

    # Drop enum types
    rule_classification = postgresql.ENUM(name='ruleclassification')
    rule_classification.drop(op.get_bind(), checkfirst=True)

    rule_category = postgresql.ENUM(name='rulecategory')
    rule_category.drop(op.get_bind(), checkfirst=True)

    review_status = postgresql.ENUM(name='reviewstatus')
    review_status.drop(op.get_bind(), checkfirst=True)
