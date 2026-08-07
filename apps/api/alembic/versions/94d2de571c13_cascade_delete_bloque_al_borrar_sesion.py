"""cascade delete bloque al borrar sesion

Revision ID: 94d2de571c13
Revises: a09181f1ca0e
Create Date: 2026-08-06 22:36:08.201202

"""

from collections.abc import Sequence

from alembic import op

revision: str = "94d2de571c13"
down_revision: str | None = "a09181f1ca0e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Un bloque no tiene existencia propia sin su sesion: borrar la sesion
    # borra sus bloques con ella (DELETE /sesiones/{id}), en vez de que el
    # service tenga que borrarlos uno por uno antes.
    op.drop_constraint(op.f("fk_bloque_sesion_id_sesion"), "bloque", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_bloque_sesion_id_sesion"),
        "bloque",
        "sesion",
        ["sesion_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_bloque_sesion_id_sesion"), "bloque", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_bloque_sesion_id_sesion"), "bloque", "sesion", ["sesion_id"], ["id"]
    )
