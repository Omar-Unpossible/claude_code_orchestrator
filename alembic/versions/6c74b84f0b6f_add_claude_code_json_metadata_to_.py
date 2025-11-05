"""add_claude_code_json_metadata_to_interaction

Revision ID: 6c74b84f0b6f
Revises: bcb1fdee05a9
Create Date: 2025-11-03 22:57:14.632557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c74b84f0b6f'
down_revision: Union[str, Sequence[str], None] = 'bcb1fdee05a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add Claude Code JSON metadata fields to interaction table

    # Token usage fields
    op.add_column('interaction', sa.Column('input_tokens', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('interaction', sa.Column('cache_creation_input_tokens', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('interaction', sa.Column('cache_read_input_tokens', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('interaction', sa.Column('output_tokens', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('interaction', sa.Column('total_tokens', sa.Integer(), nullable=True, server_default='0'))

    # Performance metrics
    op.add_column('interaction', sa.Column('duration_ms', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('interaction', sa.Column('duration_api_ms', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('interaction', sa.Column('num_turns', sa.Integer(), nullable=True, server_default='0'))

    # Session tracking
    op.add_column('interaction', sa.Column('agent_session_id', sa.String(length=64), nullable=True))
    op.create_index('ix_interaction_agent_session_id', 'interaction', ['agent_session_id'], unique=False)

    # Error handling
    op.add_column('interaction', sa.Column('error_subtype', sa.String(length=50), nullable=True))
    op.create_index('ix_interaction_error_subtype', 'interaction', ['error_subtype'], unique=False)

    # Cost tracking
    op.add_column('interaction', sa.Column('cost_usd', sa.Float(), nullable=True, server_default='0.0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove Claude Code JSON metadata fields from interaction table

    # Drop indexes first
    op.drop_index('ix_interaction_error_subtype', table_name='interaction')
    op.drop_index('ix_interaction_agent_session_id', table_name='interaction')

    # Drop columns
    op.drop_column('interaction', 'cost_usd')
    op.drop_column('interaction', 'error_subtype')
    op.drop_column('interaction', 'agent_session_id')
    op.drop_column('interaction', 'num_turns')
    op.drop_column('interaction', 'duration_api_ms')
    op.drop_column('interaction', 'duration_ms')
    op.drop_column('interaction', 'total_tokens')
    op.drop_column('interaction', 'output_tokens')
    op.drop_column('interaction', 'cache_read_input_tokens')
    op.drop_column('interaction', 'cache_creation_input_tokens')
    op.drop_column('interaction', 'input_tokens')
