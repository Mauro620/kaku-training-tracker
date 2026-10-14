"""eliminar modulo cocina

Revision ID: 7474737a7e78
Revises: 7c1d9e2f4a6b
Create Date: 2026-10-14 21:49:52.541349

Elimina las 6 tablas de nutricion (alimento, receta, receta_item,
comida_log, comida_item, despensa), sus 3 enums y el parametro
`proteina_g_por_kg`.

DESTRUCTIVA. Si alguna de las tablas tiene filas, las borra. El usuario
decidio explicitamente descartar esos datos sin respaldo, asi que la migracion
ya no se niega a correr: solo deja un aviso en el log con lo que borra. (Antes
exigia KAKU_RESPALDO_COCINA_CONFIRMADO=1; el script
`python -m scripts.respaldo_cocina` sigue disponible por si se quiere respaldar.)

El downgrade recrea el esquema vacio; los datos no se recuperan de la
migracion.
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7474737a7e78"
down_revision: str | None = "7c1d9e2f4a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Hijas primero: el orden importa por las FK.
_TABLAS = (
    "comida_item",
    "receta_item",
    "comida_log",
    "despensa",
    "receta",
    "alimento",
)
_ENUMS = ("momento_comida", "estado_pesaje", "grupo_alimento")
logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    bind = op.get_bind()
    con_datos = {
        tabla: n
        for tabla in _TABLAS
        if (n := bind.execute(sa.text(f"SELECT count(*) FROM {tabla}")).scalar())
    }
    if con_datos:
        logger.warning(
            "Eliminando datos de Cocina sin respaldo: %s",
            ", ".join(f"{t}: {n}" for t, n in con_datos.items()),
        )

    op.drop_index(
        op.f("ix_comida_log_usuario_id_fecha_momento"), table_name="comida_log"
    )
    for tabla in _TABLAS:
        op.drop_table(tabla)
    for tipo in _ENUMS:
        op.execute(f"DROP TYPE {tipo}")
    op.execute("DELETE FROM parametro WHERE clave = 'proteina_g_por_kg'")


def downgrade() -> None:
    postgresql.ENUM(
        "desayuno",
        "media_manana",
        "almuerzo",
        "merienda",
        "cena",
        name="momento_comida",
    ).create(op.get_bind())
    postgresql.ENUM("crudo", "cocido", name="estado_pesaje").create(op.get_bind())
    postgresql.ENUM(
        "proteina_animal",
        "lacteo",
        "cereal",
        "leguminosa",
        "tuberculo",
        "verdura",
        "fruta",
        "grasa",
        "procesado",
        name="grupo_alimento",
    ).create(op.get_bind())
    op.create_table(
        "alimento",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column(
            "grupo",
            postgresql.ENUM(
                "proteina_animal",
                "lacteo",
                "cereal",
                "leguminosa",
                "tuberculo",
                "verdura",
                "fruta",
                "grasa",
                "procesado",
                name="grupo_alimento",
                create_type=False,
            ),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "estado_pesaje",
            postgresql.ENUM("crudo", "cocido", name="estado_pesaje", create_type=False),
            server_default=sa.text("'crudo'::estado_pesaje"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "kcal_100g",
            sa.NUMERIC(precision=6, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "proteina_100g",
            sa.NUMERIC(precision=5, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "carbo_100g",
            sa.NUMERIC(precision=5, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "grasa_100g",
            sa.NUMERIC(precision=5, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "fibra_100g",
            sa.NUMERIC(precision=5, scale=2),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("fuente", sa.VARCHAR(length=60), autoincrement=False, nullable=True),
        sa.CheckConstraint(
            "carbo_100g >= 0::numeric", name=op.f("ck_alimento_carbo_100g_no_negativo")
        ),
        sa.CheckConstraint(
            "fibra_100g >= 0::numeric", name=op.f("ck_alimento_fibra_100g_no_negativo")
        ),
        sa.CheckConstraint(
            "grasa_100g >= 0::numeric", name=op.f("ck_alimento_grasa_100g_no_negativo")
        ),
        sa.CheckConstraint(
            "kcal_100g >= 0::numeric", name=op.f("ck_alimento_kcal_100g_no_negativo")
        ),
        sa.CheckConstraint(
            "proteina_100g >= 0::numeric",
            name=op.f("ck_alimento_proteina_100g_no_negativo"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alimento")),
        sa.UniqueConstraint(
            "nombre",
            name=op.f("uq_alimento_nombre"),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_table(
        "receta",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("nombre", sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column(
            "momento_default",
            postgresql.ENUM(
                "desayuno",
                "media_manana",
                "almuerzo",
                "merienda",
                "cena",
                name="momento_comida",
                create_type=False,
            ),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "activa",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_receta_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receta")),
        sa.UniqueConstraint(
            "usuario_id",
            "nombre",
            name=op.f("uq_receta_usuario_id_nombre"),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_table(
        "receta_item",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("receta_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("alimento_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "cantidad_g",
            sa.NUMERIC(precision=7, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.CheckConstraint(
            "cantidad_g > 0::numeric", name=op.f("ck_receta_item_cantidad_g_positiva")
        ),
        sa.ForeignKeyConstraint(
            ["alimento_id"],
            ["alimento.id"],
            name=op.f("fk_receta_item_alimento_id_alimento"),
        ),
        sa.ForeignKeyConstraint(
            ["receta_id"], ["receta.id"], name=op.f("fk_receta_item_receta_id_receta")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receta_item")),
        sa.UniqueConstraint(
            "receta_id",
            "alimento_id",
            name=op.f("uq_receta_item_receta_id_alimento_id"),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_table(
        "despensa",
        sa.Column("usuario_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("alimento_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "imprescindible",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "en_stock",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alimento_id"],
            ["alimento.id"],
            name=op.f("fk_despensa_alimento_id_alimento"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_despensa_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("usuario_id", "alimento_id", name=op.f("pk_despensa")),
    )
    op.create_table(
        "comida_log",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("usuario_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("fecha", sa.DATE(), autoincrement=False, nullable=False),
        sa.Column(
            "momento",
            postgresql.ENUM(
                "desayuno",
                "media_manana",
                "almuerzo",
                "merienda",
                "cena",
                name="momento_comida",
                create_type=False,
            ),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("receta_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("nota", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("idempotency_key", sa.UUID(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["receta_id"], ["receta.id"], name=op.f("fk_comida_log_receta_id_receta")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_comida_log_usuario_id_usuario"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comida_log")),
        sa.UniqueConstraint(
            "idempotency_key",
            name=op.f("uq_comida_log_idempotency_key"),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        op.f("ix_comida_log_usuario_id_fecha_momento"),
        "comida_log",
        ["usuario_id", "fecha", "momento"],
        unique=False,
    )
    op.create_table(
        "comida_item",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column("comida_log_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("alimento_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "cantidad_g",
            sa.NUMERIC(precision=7, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.CheckConstraint(
            "cantidad_g > 0::numeric", name=op.f("ck_comida_item_cantidad_g_positiva")
        ),
        sa.ForeignKeyConstraint(
            ["alimento_id"],
            ["alimento.id"],
            name=op.f("fk_comida_item_alimento_id_alimento"),
        ),
        sa.ForeignKeyConstraint(
            ["comida_log_id"],
            ["comida_log.id"],
            name=op.f("fk_comida_item_comida_log_id_comida_log"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comida_item")),
    )
