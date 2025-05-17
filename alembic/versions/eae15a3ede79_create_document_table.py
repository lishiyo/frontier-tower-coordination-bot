"""create_document_table

Revision ID: eae15a3ede79
Revises: cb7185863232
Create Date: 2025-05-17 00:04:00.662993

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eae15a3ede79'
down_revision: Union[str, None] = 'cb7185863232'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('upload_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('vector_ids', sa.JSON(), nullable=True),
        sa.Column('proposal_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_content_hash'), 'documents', ['content_hash'], unique=False) # unique=False typically for non-PK indexes, but can be True for content_hash if desired
    op.create_index(op.f('ix_documents_proposal_id'), 'documents', ['proposal_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_documents_proposal_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_content_hash'), table_name='documents')
    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')
