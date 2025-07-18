"""change_proposal_proposer_id_to_biginteger

Revision ID: f558c5a9a4d6
Revises: 2de06a4f92b0
Create Date: 2025-05-17 19:13:01.875563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f558c5a9a4d6'
down_revision: Union[str, None] = '2de06a4f92b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('proposals',
                    'proposer_telegram_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('proposals',
                    'proposer_telegram_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.INTEGER(),
                    existing_nullable=False)
    # ### end Alembic commands ###
