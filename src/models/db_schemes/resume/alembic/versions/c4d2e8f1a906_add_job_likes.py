"""Add job_likes for candidate-saved jobs

Revision ID: c4d2e8f1a906
Revises: b3f1a2c4d5e6
Create Date: 2026-10-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d2e8f1a906'
down_revision: Union[str, Sequence[str], None] = 'b3f1a2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'job_likes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('jd_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customer_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['jd_id'], ['job_descriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id', 'jd_id', name='uq_job_likes_customer_jd'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('job_likes')
