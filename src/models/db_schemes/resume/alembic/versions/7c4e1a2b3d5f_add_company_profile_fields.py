"""Add website, industry, location to company_profiles

Revision ID: 7c4e1a2b3d5f
Revises: f9a69b3496ce
Create Date: 2026-10-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c4e1a2b3d5f'
down_revision: Union[str, Sequence[str], None] = 'f9a69b3496ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('company_profiles', sa.Column('website', sa.String(), nullable=True))
    op.add_column('company_profiles', sa.Column('industry', sa.String(), nullable=True))
    op.add_column('company_profiles', sa.Column('location', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('company_profiles', 'location')
    op.drop_column('company_profiles', 'industry')
    op.drop_column('company_profiles', 'website')
