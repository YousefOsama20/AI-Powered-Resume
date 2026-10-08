"""Add photo_path to customer and company profiles

Revision ID: b3f1a2c4d5e6
Revises: a91f2c7d4e10
Create Date: 2026-10-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f1a2c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'a91f2c7d4e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('customer_profiles', sa.Column('photo_path', sa.String(), nullable=True))
    op.add_column('company_profiles', sa.Column('photo_path', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('company_profiles', 'photo_path')
    op.drop_column('customer_profiles', 'photo_path')
