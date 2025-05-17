"""create_submission_table

Revision ID: 5349f8fc14f3
Revises: b05ebfd81299
Create Date: 2025-05-17 16:16:09.135718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5349f8fc14f3'
down_revision: Union[str, None] = 'b05ebfd81299'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'submissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('submitter_id', sa.Integer(), nullable=False),
        sa.Column('response_content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id'], ),
        sa.ForeignKeyConstraint(['submitter_id'], ['users.telegram_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proposal_id', 'submitter_id', name='uq_proposal_submitter')
    )
    op.create_index(op.f('ix_submissions_id'), 'submissions', ['id'], unique=False)
    op.create_index(op.f('ix_submissions_proposal_id'), 'submissions', ['proposal_id'], unique=False)
    op.create_index(op.f('ix_submissions_submitter_id'), 'submissions', ['submitter_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_submissions_submitter_id'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_proposal_id'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_id'), table_name='submissions')
    op.drop_table('submissions')
