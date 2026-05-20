"""add users.password_hash

Revision ID: c8d4e2f7a9b1
Revises: b3f1a2c4d5e6
Create Date: 2026-05-20 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import bcrypt

revision: str = 'c8d4e2f7a9b1'
down_revision: Union[str, None] = 'b3f1a2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))

    # Backfill existing rows with bcrypt hash of "password" so seeded users
    # remain usable after the migration. Fresh installs hit a no-op here.
    default_hash = bcrypt.hashpw(b'password', bcrypt.gensalt()).decode('utf-8')
    op.execute(
        sa.text("UPDATE users SET password_hash = :h WHERE password_hash IS NULL")
        .bindparams(h=default_hash)
    )

    op.alter_column('users', 'password_hash', nullable=False)


def downgrade() -> None:
    op.drop_column('users', 'password_hash')
