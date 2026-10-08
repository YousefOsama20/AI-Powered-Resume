"""Add apply_advice_cache table

Revision ID: a91f2c7d4e10
Revises: 7c4e1a2b3d5f
Create Date: 2026-10-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a91f2c7d4e10'
down_revision: Union[str, Sequence[str], None] = '7c4e1a2b3d5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'apply_advice_cache',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('jd_id', sa.String(), nullable=False),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('advice_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customer_profiles.id'], ),
        sa.ForeignKeyConstraint(['document_id'], ['candidate_documents.id'], ),
        sa.ForeignKeyConstraint(['jd_id'], ['job_descriptions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id', 'jd_id', 'document_id', name='uq_advice_customer_jd_doc'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('apply_advice_cache')
