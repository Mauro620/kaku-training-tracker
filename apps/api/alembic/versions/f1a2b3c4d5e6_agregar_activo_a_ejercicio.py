"""agregar activo a ejercicio

Revision ID: f1a2b3c4d5e6
Revises: e4a7b93c218d
Create Date: 2026-08-26 12:00:00.000000

Para el banco de ejercicios del feature 2: ocultar un ejercicio del selector
sin borrarlo (lo decide el endpoint de fusion: el origen queda archivado con
activo=false). La historia del usuario se preserva porque `bloque.ejercicio_id`
y `bloque_plan.ejercicio_id` siguen apuntando al original.

default true: los registros preexistentes siguen visibles, que es lo que
espera el selector del frontend (filtro `activo=true` por default).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e4a7b93c218d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ejercicio",
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("ejercicio", "activo")
