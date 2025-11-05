"""add_task_id_to_session_record

Revision ID: f56283a43d46
Revises: 72c8cc90c58f
Create Date: 2025-11-04 16:15:26.933431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f56283a43d46'
down_revision: Union[str, Sequence[str], None] = '72c8cc90c58f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add task_id to session_record for per-iteration tracking."""
    # SQLite requires batch mode for foreign key operations
    with op.batch_alter_table('session_record', schema=None) as batch_op:
        # Add task_id column
        batch_op.add_column(sa.Column('task_id', sa.Integer(), nullable=True))

        # Add foreign key constraint
        batch_op.create_foreign_key(
            'fk_session_record_task_id',
            'task',
            ['task_id'], ['id']
        )

        # Add index for efficient task-level aggregation queries
        batch_op.create_index('ix_session_record_task_id', ['task_id'])


def downgrade() -> None:
    """Downgrade schema - remove task_id from session_record."""
    # SQLite requires batch mode for foreign key operations
    with op.batch_alter_table('session_record', schema=None) as batch_op:
        # Remove index
        batch_op.drop_index('ix_session_record_task_id')

        # Remove foreign key
        batch_op.drop_constraint('fk_session_record_task_id', type_='foreignkey')

        # Remove column
        batch_op.drop_column('task_id')
