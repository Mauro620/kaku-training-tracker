from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    Numeric,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import OrigenDato
from app.models.types import BigIntPk, Peso, UsuarioFk


class MedidaCorporal(Base):
    """Semanal, en ayunas, misma hora. El ruido diario es agua. El peso es lo
    obligatorio; la cintura y la FC de reposo son opcionales.

    La unicidad `(usuario_id, fecha)` es la deduplicación natural de la cola de
    sync. `origen` distingue el dato manual del importado de Health.
    """

    __tablename__ = "medida_corporal"
    __table_args__ = (
        UniqueConstraint("usuario_id", "fecha"),
        CheckConstraint("peso_kg > 0", name="peso_kg_positivo"),
        CheckConstraint(
            "fc_reposo IS NULL OR fc_reposo > 0", name="fc_reposo_positiva"
        ),
        CheckConstraint(
            "cintura_cm IS NULL OR cintura_cm > 0", name="cintura_cm_positiva"
        ),
    )

    id: Mapped[BigIntPk]
    usuario_id: Mapped[UsuarioFk]
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    peso_kg: Mapped[Peso] = mapped_column(nullable=False)
    fc_reposo: Mapped[int | None] = mapped_column(SmallInteger)
    # Perimetro de cintura, opcional. Alimenta la seccion de composicion de
    # Progreso y el resumen de ciclo.
    cintura_cm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    origen: Mapped[OrigenDato] = mapped_column(
        Enum(OrigenDato, name="origen_dato"),
        nullable=False,
        server_default=OrigenDato.manual.value,
    )
