"""add_session_management

Revision ID: 40180dbb4798
Revises: 6c74b84f0b6f
Create Date: 2025-11-03 23:05:10.608922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40180dbb4798'
down_revision: Union[str, Sequence[str], None] = '6c74b84f0b6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create session_record table for milestone-based session tracking
    op.create_table('session_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('milestone_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_turns', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project_state.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )

    # Create indexes for efficient querying
    op.create_index('ix_session_record_session_id', 'session_record', ['session_id'], unique=True)
    op.create_index('ix_session_record_project_id', 'session_record', ['project_id'], unique=False)
    op.create_index('ix_session_record_milestone_id', 'session_record', ['milestone_id'], unique=False)
    op.create_index('ix_session_record_started_at', 'session_record', ['started_at'], unique=False)
    op.create_index('ix_session_record_status', 'session_record', ['status'], unique=False)
    op.create_index('idx_session_project_status', 'session_record', ['project_id', 'status'], unique=False)
    op.create_index('idx_session_milestone', 'session_record', ['milestone_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_session_milestone', table_name='session_record')
    op.drop_index('idx_session_project_status', table_name='session_record')
    op.drop_index('ix_session_record_status', table_name='session_record')
    op.drop_index('ix_session_record_started_at', table_name='session_record')
    op.drop_index('ix_session_record_milestone_id', table_name='session_record')
    op.drop_index('ix_session_record_project_id', table_name='session_record')
    op.drop_index('ix_session_record_session_id', table_name='session_record')

    # Drop table
    op.drop_table('session_record')
