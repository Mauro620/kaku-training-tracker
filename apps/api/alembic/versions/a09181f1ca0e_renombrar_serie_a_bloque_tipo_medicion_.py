"""renombrar serie a bloque, tipo_medicion en ejercicio

Revision ID: a09181f1ca0e
Revises: 08f4f196bca4
Create Date: 2026-08-06 22:01:04.107862

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.seeds.ejercicios import EJERCICIOS

revision: str = "a09181f1ca0e"
down_revision: str | None = "08f4f196bca4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # ---------- ejercicio: tipo_medicion + tipo_sesion_id nullable ----------
    tipo_medicion_enum = postgresql.ENUM(
        "carga", "distancia", "tiempo", "tecnica", name="tipo_medicion"
    )
    tipo_medicion_enum.create(bind, checkfirst=True)
    op.add_column(
        "ejercicio", sa.Column("tipo_medicion", tipo_medicion_enum, nullable=True)
    )
    # El ejercicio que el usuario crea inline (POST /catalogos/ejercicios)
    # no pide tipo_sesion: era solo una categorizacion de referencia.
    op.alter_column("ejercicio", "tipo_sesion_id", nullable=True)

    for nombre, _patron, _carga_lumbar, _tipo_codigo, tipo_medicion in EJERCICIOS:
        bind.execute(
            sa.text("UPDATE ejercicio SET tipo_medicion = :tm WHERE nombre = :nombre"),
            {"tm": tipo_medicion.value, "nombre": nombre},
        )

    op.alter_column("ejercicio", "tipo_medicion", nullable=False)

    # ---------- serie -> bloque ----------
    # "N series x M reps" no describe un sprint ni un control tecnico
    # (REGLAS_NEGOCIO §15). Rename + columnas nuevas + series/reps nullable.
    # Las renombradas via ALTER TABLE ... RENAME CONSTRAINT son SQL crudo:
    # no pasan por el formateador de naming convention de alembic, así que
    # no llevan op.f(). Las que se crean/dropean via la API de alembic sí
    # (si no, alembic vuelve a aplicarles la convención y duplica el prefijo).
    op.rename_table("serie", "bloque")
    op.execute("ALTER TABLE bloque RENAME CONSTRAINT pk_serie TO pk_bloque")
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT fk_serie_sesion_id_sesion "
        "TO fk_bloque_sesion_id_sesion"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT fk_serie_ejercicio_id_ejercicio "
        "TO fk_bloque_ejercicio_id_ejercicio"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT uq_serie_sesion_id_orden "
        "TO uq_bloque_sesion_id_orden"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT ck_serie_rpe_rango TO ck_bloque_rpe_rango"
    )

    op.alter_column("bloque", "series", nullable=True)
    op.alter_column("bloque", "reps", nullable=True)
    op.add_column("bloque", sa.Column("distancia_m", sa.Numeric(5, 1), nullable=True))
    op.add_column("bloque", sa.Column("duracion_s", sa.Integer(), nullable=True))
    op.add_column("bloque", sa.Column("calidad", sa.SmallInteger(), nullable=True))

    # series/reps positivas: nunca se renombraron arriba (la condicion vieja
    # "series > 0" no tolera NULL), asi que siguen con el nombre viejo hasta
    # que se recrean acá con el nombre y la condicion nuevos.
    op.drop_constraint(op.f("ck_serie_series_positivas"), "bloque", type_="check")
    op.create_check_constraint(
        op.f("ck_bloque_series_positivas"), "bloque", "series IS NULL OR series > 0"
    )
    op.drop_constraint(op.f("ck_serie_reps_positivas"), "bloque", type_="check")
    op.create_check_constraint(
        op.f("ck_bloque_reps_positivas"), "bloque", "reps IS NULL OR reps > 0"
    )
    op.create_check_constraint(
        op.f("ck_bloque_distancia_m_positiva"),
        "bloque",
        "distancia_m IS NULL OR distancia_m > 0",
    )
    op.create_check_constraint(
        op.f("ck_bloque_duracion_s_positiva"),
        "bloque",
        "duracion_s IS NULL OR duracion_s > 0",
    )
    op.create_check_constraint(
        op.f("ck_bloque_calidad_rango"),
        "bloque",
        "calidad IS NULL OR calidad BETWEEN 1 AND 5",
    )

    # ---------- serie_plan -> bloque_plan ----------
    op.rename_table("serie_plan", "bloque_plan")
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT pk_serie_plan TO pk_bloque_plan"
    )
    op.execute(
        "ALTER TABLE bloque_plan "
        "RENAME CONSTRAINT fk_serie_plan_sesion_plan_id_sesion_plan "
        "TO fk_bloque_plan_sesion_plan_id_sesion_plan"
    )
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT fk_serie_plan_ejercicio_id_ejercicio "
        "TO fk_bloque_plan_ejercicio_id_ejercicio"
    )
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT uq_serie_plan_sesion_plan_id_orden "
        "TO uq_bloque_plan_sesion_plan_id_orden"
    )
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT ck_serie_plan_reps_ordenadas "
        "TO ck_bloque_plan_reps_ordenadas"
    )

    op.alter_column("bloque_plan", "series", nullable=True)
    op.add_column(
        "bloque_plan",
        sa.Column("distancia_objetivo_m", sa.Numeric(5, 1), nullable=True),
    )
    op.add_column(
        "bloque_plan",
        sa.Column("duracion_objetivo_s", sa.SmallInteger(), nullable=True),
    )

    op.drop_constraint(
        op.f("ck_serie_plan_series_positivas"), "bloque_plan", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_bloque_plan_series_positivas"),
        "bloque_plan",
        "series IS NULL OR series > 0",
    )
    op.create_check_constraint(
        op.f("ck_bloque_plan_distancia_objetivo_m_positiva"),
        "bloque_plan",
        "distancia_objetivo_m IS NULL OR distancia_objetivo_m > 0",
    )
    op.create_check_constraint(
        op.f("ck_bloque_plan_duracion_objetivo_s_positiva"),
        "bloque_plan",
        "duracion_objetivo_s IS NULL OR duracion_objetivo_s > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_bloque_plan_duracion_objetivo_s_positiva"),
        "bloque_plan",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_bloque_plan_distancia_objetivo_m_positiva"),
        "bloque_plan",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_bloque_plan_series_positivas"), "bloque_plan", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_bloque_plan_series_positivas"), "bloque_plan", "series > 0"
    )
    op.drop_column("bloque_plan", "duracion_objetivo_s")
    op.drop_column("bloque_plan", "distancia_objetivo_m")
    op.alter_column("bloque_plan", "series", nullable=False)

    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT ck_bloque_plan_series_positivas "
        "TO ck_serie_plan_series_positivas"
    )
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT ck_bloque_plan_reps_ordenadas "
        "TO ck_serie_plan_reps_ordenadas"
    )
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT uq_bloque_plan_sesion_plan_id_orden "
        "TO uq_serie_plan_sesion_plan_id_orden"
    )
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT fk_bloque_plan_ejercicio_id_ejercicio "
        "TO fk_serie_plan_ejercicio_id_ejercicio"
    )
    op.execute(
        "ALTER TABLE bloque_plan "
        "RENAME CONSTRAINT fk_bloque_plan_sesion_plan_id_sesion_plan "
        "TO fk_serie_plan_sesion_plan_id_sesion_plan"
    )
    op.execute(
        "ALTER TABLE bloque_plan RENAME CONSTRAINT pk_bloque_plan TO pk_serie_plan"
    )
    op.rename_table("bloque_plan", "serie_plan")

    op.drop_constraint(op.f("ck_bloque_calidad_rango"), "bloque", type_="check")
    op.drop_constraint(op.f("ck_bloque_duracion_s_positiva"), "bloque", type_="check")
    op.drop_constraint(op.f("ck_bloque_distancia_m_positiva"), "bloque", type_="check")
    op.drop_constraint(op.f("ck_bloque_reps_positivas"), "bloque", type_="check")
    op.create_check_constraint(op.f("ck_bloque_reps_positivas"), "bloque", "reps > 0")
    op.drop_constraint(op.f("ck_bloque_series_positivas"), "bloque", type_="check")
    op.create_check_constraint(
        op.f("ck_bloque_series_positivas"), "bloque", "series > 0"
    )

    op.drop_column("bloque", "calidad")
    op.drop_column("bloque", "duracion_s")
    op.drop_column("bloque", "distancia_m")
    op.alter_column("bloque", "reps", nullable=False)
    op.alter_column("bloque", "series", nullable=False)

    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT ck_bloque_rpe_rango TO ck_serie_rpe_rango"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT ck_bloque_series_positivas "
        "TO ck_serie_series_positivas"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT ck_bloque_reps_positivas "
        "TO ck_serie_reps_positivas"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT uq_bloque_sesion_id_orden "
        "TO uq_serie_sesion_id_orden"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT fk_bloque_ejercicio_id_ejercicio "
        "TO fk_serie_ejercicio_id_ejercicio"
    )
    op.execute(
        "ALTER TABLE bloque RENAME CONSTRAINT fk_bloque_sesion_id_sesion "
        "TO fk_serie_sesion_id_sesion"
    )
    op.execute("ALTER TABLE bloque RENAME CONSTRAINT pk_bloque TO pk_serie")
    op.rename_table("bloque", "serie")

    op.alter_column("ejercicio", "tipo_sesion_id", nullable=False)
    op.drop_column("ejercicio", "tipo_medicion")
    postgresql.ENUM(name="tipo_medicion").drop(op.get_bind(), checkfirst=True)
