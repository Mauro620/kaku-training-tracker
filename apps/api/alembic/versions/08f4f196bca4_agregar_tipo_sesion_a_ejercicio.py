"""agregar tipo_sesion a ejercicio

Revision ID: 08f4f196bca4
Revises: 844c752ec28c
Create Date: 2026-08-06 09:07:59.449237

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.seeds.ejercicios import EJERCICIOS

revision: str = "08f4f196bca4"
down_revision: str | None = "844c752ec28c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable primero: la tabla ya tiene filas sembradas (Fase 1). El
    # backfill de abajo, tomado del mismo mapeo nombre->tipo_codigo que usa
    # el seed, es lo que permite endurecer a NOT NULL al final sin perder
    # una fila existente por el camino.
    op.add_column(
        "ejercicio", sa.Column("tipo_sesion_id", sa.SmallInteger(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_ejercicio_tipo_sesion_id_tipo_sesion"),
        "ejercicio",
        "tipo_sesion",
        ["tipo_sesion_id"],
        ["id"],
    )

    conexion = op.get_bind()
    for nombre, _patron, _carga_lumbar, tipo_codigo in EJERCICIOS:
        conexion.execute(
            sa.text(
                "UPDATE ejercicio SET tipo_sesion_id = "
                "(SELECT id FROM tipo_sesion WHERE codigo = :codigo) "
                "WHERE nombre = :nombre"
            ),
            {"codigo": tipo_codigo, "nombre": nombre},
        )

    op.alter_column("ejercicio", "tipo_sesion_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_ejercicio_tipo_sesion_id_tipo_sesion"), "ejercicio", type_="foreignkey"
    )
    op.drop_column("ejercicio", "tipo_sesion_id")
