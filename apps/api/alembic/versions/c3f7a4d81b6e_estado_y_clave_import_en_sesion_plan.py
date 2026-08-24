"""estado y clave_import en sesion_plan

Revision ID: c3f7a4d81b6e
Revises: 772c63592825
Create Date: 2026-08-24 14:30:00.000000

Habilita la importacion de plan semanal por JSON
(docs/feature_1_session_plan_json/PLAN_IMPORT.md §2):

- `estado`: en que quedo el plan. `descartado` lo declara el usuario;
  `cumplido` y `movido` los escribe el service de sesion.
- `clave_import`: identidad del plan dentro de la semana para el importador,
  con indice unico PARCIAL para que los planes creados a mano (clave NULL) no
  choquen entre si.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3f7a4d81b6e"
down_revision: str | None = "772c63592825"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ESTADO_SESION_PLAN = sa.Enum(
    "pendiente",
    "cumplido",
    "movido",
    "descartado",
    name="estado_sesion_plan",
)


def upgrade() -> None:
    # create_type=False en la Column de abajo no alcanza: el tipo hay que
    # crearlo explicitamente antes de referenciarlo en el ADD COLUMN.
    ESTADO_SESION_PLAN.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "sesion_plan",
        sa.Column(
            "estado",
            ESTADO_SESION_PLAN,
            nullable=False,
            server_default="pendiente",
        ),
    )
    op.add_column(
        "sesion_plan", sa.Column("clave_import", sa.String(length=80), nullable=True)
    )

    # Los planes que ya existen y tienen una sesion real asociada arrancan en
    # su estado verdadero, no en 'pendiente': sin este backfill el importador
    # veria como reemplazables planes que ya se ejecutaron.
    # Subconsulta correlacionada y no UPDATE..FROM con LEFT JOIN: Postgres no
    # deja referenciar la tabla que se actualiza dentro del ON de un outer
    # join del from_list.
    conexion = op.get_bind()
    conexion.execute(
        sa.text(
            """
            UPDATE sesion_plan AS p
            SET estado = CASE
                -- Sin dia_sugerido o sin semana no hay dia planeado contra el
                -- cual comparar: se ejecuto, y eso es todo lo que se sabe.
                WHEN p.dia_sugerido IS NULL OR p.ciclo_semana_id IS NULL
                    THEN 'cumplido'::estado_sesion_plan
                WHEN (
                    SELECT s.fecha - (c.fecha_inicio + (cs.numero - 1) * 7)
                    FROM sesion AS s
                    JOIN ciclo_semana AS cs ON cs.id = p.ciclo_semana_id
                    JOIN ciclo AS c ON c.id = cs.ciclo_id
                    WHERE s.sesion_plan_id = p.id
                ) = p.dia_sugerido THEN 'cumplido'::estado_sesion_plan
                ELSE 'movido'::estado_sesion_plan
            END
            WHERE EXISTS (
                SELECT 1 FROM sesion AS s WHERE s.sesion_plan_id = p.id
            )
            """
        )
    )

    op.create_index(
        "ix_sesion_plan_clave_import",
        "sesion_plan",
        ["ciclo_semana_id", "clave_import"],
        unique=True,
        postgresql_where=sa.text("clave_import IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_sesion_plan_clave_import", table_name="sesion_plan")
    op.drop_column("sesion_plan", "clave_import")
    op.drop_column("sesion_plan", "estado")
    ESTADO_SESION_PLAN.drop(op.get_bind(), checkfirst=True)
