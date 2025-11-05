"""add_context_window_tracking

Revision ID: 72c8cc90c58f
Revises: 40180dbb4798
Create Date: 2025-11-03 23:19:22.884458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72c8cc90c58f'
down_revision: Union[str, Sequence[str], None] = '40180dbb4798'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create context_window_usage table for manual token tracking
    op.create_table('context_window_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('cumulative_tokens', sa.Integer(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_creation_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_read_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    op.create_index('ix_context_window_usage_session_id', 'context_window_usage', ['session_id'], unique=False)
    op.create_index('ix_context_window_usage_cumulative_tokens', 'context_window_usage', ['cumulative_tokens'], unique=False)
    op.create_index('ix_context_window_usage_timestamp', 'context_window_usage', ['timestamp'], unique=False)
    op.create_index('idx_context_window_session_time', 'context_window_usage', ['session_id', 'timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_context_window_session_time', table_name='context_window_usage')
    op.drop_index('ix_context_window_usage_timestamp', table_name='context_window_usage')
    op.drop_index('ix_context_window_usage_cumulative_tokens', table_name='context_window_usage')
    op.drop_index('ix_context_window_usage_session_id', table_name='context_window_usage')

    # Drop table
    op.drop_table('context_window_usage')
