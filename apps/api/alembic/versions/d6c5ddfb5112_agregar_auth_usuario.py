"""agregar auth_usuario

Revision ID: d6c5ddfb5112
Revises: a1b113ff814a
Create Date: 2026-08-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6c5ddfb5112"
down_revision: str | None = "a1b113ff814a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tabla separada de `usuario` para que la identidad de login (email,
    # password, refresh) no contamine la tabla de dominio. PK = FK a usuario:
    # la relación es 1:1, no autoincremental ni UUID generado por el server.
    op.create_table(
        "auth_usuario",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "refresh_token_expira_en",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ultimo_acceso_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_auth_usuario_usuario_id_usuario"),
        ),
        sa.PrimaryKeyConstraint("usuario_id", name=op.f("pk_auth_usuario")),
        sa.UniqueConstraint("email", name=op.f("uq_auth_usuario_email")),
    )


def downgrade() -> None:
    op.drop_table("auth_usuario")
