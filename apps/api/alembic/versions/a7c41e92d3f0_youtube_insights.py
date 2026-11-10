"""youtube insights

Revision ID: a7c41e92d3f0
Revises: 0ce059f894cb
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c41e92d3f0'
down_revision: Union[str, Sequence[str], None] = '0ce059f894cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('youtube_insights',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('videos', sa.JSON(), nullable=False),
    sa.Column('analysed_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_youtube_insights_workspace_id'), 'youtube_insights', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_youtube_insights_workspace_id'), table_name='youtube_insights')
    op.drop_table('youtube_insights')
