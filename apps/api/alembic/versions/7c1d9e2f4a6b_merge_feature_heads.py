"""merge feature heads

Revision ID: 7c1d9e2f4a6b
Revises: 24d0c867b11e, f1a2b3c4d5e6
Create Date: 2026-08-26 14:30:00.000000

Merge the pre-existing plan-note head with the feature 2 exercise archive
head so ``alembic upgrade head`` has one unambiguous target.
"""

from collections.abc import Sequence

revision: str = "7c1d9e2f4a6b"
down_revision: tuple[str, str] = ("24d0c867b11e", "f1a2b3c4d5e6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
