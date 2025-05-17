"""create_proposal_table

Revision ID: 0cb97eaf1e36
Revises: 8aa34f61aaa0
Create Date: 2025-05-16 21:20:10.064166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cb97eaf1e36'
down_revision: Union[str, None] = '8aa34f61aaa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'proposals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('proposer_telegram_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('proposal_type', sa.String(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('channel_message_id', sa.Integer(), nullable=True),
        sa.Column('creation_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deadline_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('raw_results', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['proposer_telegram_id'], ['users.telegram_id'], )
    )
    op.create_index(op.f('ix_proposals_id'), 'proposals', ['id'], unique=False)
    op.create_index(op.f('ix_proposals_proposer_telegram_id'), 'proposals', ['proposer_telegram_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_proposals_proposer_telegram_id'), table_name='proposals')
    op.drop_index(op.f('ix_proposals_id'), table_name='proposals')
    op.drop_table('proposals') 