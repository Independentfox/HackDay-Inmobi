"""add global_stats table for running Bayesian mean

Revision ID: d1e2f3a4b5c6
Revises: c8d4e2f7a9b1
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c8d4e2f7a9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'global_stats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('total_rating_sum', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_rating_count', sa.Integer(), nullable=False, server_default='0'),
    )
    # Seed from existing movie data so the running totals are correct on deploy
    op.execute("""
        INSERT INTO global_stats (id, total_rating_sum, total_rating_count)
        SELECT 1, COALESCE(SUM(rating_sum), 0.0), COALESCE(SUM(rating_count), 0)
        FROM movies
    """)


def downgrade() -> None:
    op.drop_table('global_stats')
