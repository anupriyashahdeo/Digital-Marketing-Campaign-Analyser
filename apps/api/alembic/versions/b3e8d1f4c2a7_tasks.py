"""tasks: CSV analysis queue for the external model worker

Revision ID: b3e8d1f4c2a7
Revises: a7c41e92d3f0
Create Date: 2026-11-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e8d1f4c2a7'
down_revision: Union[str, Sequence[str], None] = 'a7c41e92d3f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tasks',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('task_input', sa.Text(), nullable=True),
    sa.Column('task_complete', sa.Integer(), nullable=False),
    sa.Column('task_output', sa.JSON(), nullable=True),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('save_to_dashboard', sa.Boolean(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('lease_token', sa.String(length=64), nullable=True),
    sa.Column('claimed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_workspace_id'), 'tasks', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_tasks_created_by'), 'tasks', ['created_by'], unique=False)
    op.create_index('ix_tasks_queue', 'tasks', ['task_complete', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_tasks_queue', table_name='tasks')
    op.drop_index(op.f('ix_tasks_created_by'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_workspace_id'), table_name='tasks')
    op.drop_table('tasks')
