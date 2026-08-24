"""anclar fecha_inicio de ciclo al lunes ISO

Revision ID: d81f2a6c95b4
Revises: c3f7a4d81b6e
Create Date: 2026-08-24 16:10:00.000000

`sesion_plan.dia_sugerido` es un offset desde el inicio de la semana y esta
documentado como 0=lunes (REGLAS_NEGOCIO §13.3). El rango de la semana N se
deriva de `ciclo.fecha_inicio` (`calcular_rango_semana`), asi que esa
equivalencia solo se sostiene si `fecha_inicio` cae lunes.

Con un ciclo que arranca domingo, el plan del "lunes" aterriza el domingo y
`resolver_estado_de_plan` marca `movido` una sesion que se cumplio en fecha.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d81f2a6c95b4"
down_revision: str | None = "c3f7a4d81b6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Corre ANTES del CHECK: los ciclos que ya existen lo violarian.
    # ISODOW: lunes=1 .. domingo=7, asi que restar (isodow - 1) da el lunes de
    # esa misma semana ISO. fecha_fin_prevista es generada y se recalcula sola.
    op.execute(
        sa.text(
            "UPDATE ciclo "
            "SET fecha_inicio = fecha_inicio "
            "  - (EXTRACT(ISODOW FROM fecha_inicio)::int - 1) "
            "WHERE EXTRACT(ISODOW FROM fecha_inicio) <> 1"
        )
    )
    op.create_check_constraint(
        "fecha_inicio_es_lunes", "ciclo", "EXTRACT(ISODOW FROM fecha_inicio) = 1"
    )


def downgrade() -> None:
    # Las fechas corridas no se restauran: la original se perdio y adivinarla
    # moveria el calendario de sesiones que ya se registraron.
    op.drop_constraint("fecha_inicio_es_lunes", "ciclo", type_="check")
