"""descripcion de ejercicio

Revision ID: e4a7b93c218d
Revises: d81f2a6c95b4
Create Date: 2026-08-24 17:05:00.000000

Como se ejecuta cada ejercicio. La escribe el LLM al planear la semana
(campo opcional del bloque en el JSON de importacion) y queda guardada para
siempre: buscar la tecnica en el momento es friccion en la cancha, y el
registro diario no puede pasar de 2 minutos (AGENTS.md §1).

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4a7b93c218d"
down_revision: str | None = "d81f2a6c95b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ejercicio", sa.Column("descripcion", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ejercicio", "descripcion")
