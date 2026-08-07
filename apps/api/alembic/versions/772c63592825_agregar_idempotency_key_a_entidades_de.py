"""agregar idempotency_key a entidades de captura

Revision ID: 772c63592825
Revises: 94d2de571c13
Create Date: 2026-08-07 14:00:00.000000

Revision que agrega idempotency_key a las 5 entidades de captura que no
lo tenian: registro_sueno, registro_bienestar, registro_hidratacion,
habito_registro (rompe la decision del DBML original de no llevarlo) y
molestia. Nullable para preservar los registros existentes y admitir el
backfill de Fase 9 (Notion) sin UUID.

La deduplicacion sigue siendo por la PK o unicidad natural de la tabla:
(usuario_id, fecha) para sueno/bienestar/hidratacion, PK compuesta
(habito_id, fecha) para habito_registro, (usuario_id, fecha, zona_id)
para molestia. El idempotency_key es metadata para la cola de Fase 5,
no una segunda unicidad.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "772c63592825"
down_revision: str | None = "94d2de571c13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # nullable=True: admite los registros existentes y el backfill futuro
    # de Fase 9 (Notion) sin UUID. Postgres acepta multiples NULLs en un
    # UNIQUE, asi que no hay conflicto entre filas sin key.
    op.add_column(
        "registro_sueno",
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_registro_sueno_idempotency_key"),
        "registro_sueno",
        ["idempotency_key"],
    )

    op.add_column(
        "registro_bienestar",
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_registro_bienestar_idempotency_key"),
        "registro_bienestar",
        ["idempotency_key"],
    )

    op.add_column(
        "registro_hidratacion",
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_registro_hidratacion_idempotency_key"),
        "registro_hidratacion",
        ["idempotency_key"],
    )

    op.add_column(
        "habito_registro",
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_habito_registro_idempotency_key"),
        "habito_registro",
        ["idempotency_key"],
    )

    op.add_column(
        "molestia",
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_molestia_idempotency_key"),
        "molestia",
        ["idempotency_key"],
    )


def downgrade() -> None:
    for tabla, nombre in [
        ("registro_sueno", "uq_registro_sueno_idempotency_key"),
        ("registro_bienestar", "uq_registro_bienestar_idempotency_key"),
        ("registro_hidratacion", "uq_registro_hidratacion_idempotency_key"),
        ("habito_registro", "uq_habito_registro_idempotency_key"),
        ("molestia", "uq_molestia_idempotency_key"),
    ]:
        op.drop_constraint(nombre, tabla, type_="unique")
        op.drop_column(tabla, "idempotency_key")
