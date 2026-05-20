"""add review_helpful_votes table

Revision ID: b3f1a2c4d5e6
Revises: 2e6e87d1cc7d
Create Date: 2026-05-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3f1a2c4d5e6'
down_revision: Union[str, None] = '2e6e87d1cc7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'review_helpful_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'review_id', name='uq_user_review_helpful'),
    )
    op.create_index(op.f('ix_review_helpful_votes_id'), 'review_helpful_votes', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_review_helpful_votes_id'), table_name='review_helpful_votes')
    op.drop_table('review_helpful_votes')
