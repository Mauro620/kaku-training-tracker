from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import OrigenDato
from app.models.types import BigIntPk, UsuarioFk


class RegistroSueno(Base):
    """`timestamptz` en vez de dos campos `time`: cruzar medianoche con dos
    `time` obliga a lógica condicional en cada consulta.

    INVARIANTE DE SERVICIO: `fecha` es la del despertar, o sea la fecha local
    de `fin`. No se puede imponer con CHECK ni con columna generada porque la
    conversión de zona horaria no es IMMUTABLE en Postgres. El servicio que
    escribe sueño es el responsable.

    La unicidad `(usuario_id, fecha)` es la deduplicación natural de la cola de
    sync: la operación es un upsert y no hace falta `idempotency_key`.
    """

    __tablename__ = "registro_sueno"
    __table_args__ = (
        UniqueConstraint("usuario_id", "fecha"),
        CheckConstraint("fin > inicio", name="fin_posterior_a_inicio"),
    )

    id: Mapped[BigIntPk]
    usuario_id: Mapped[UsuarioFk]
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Único lugar donde vive este dato. NO existe como hábito: se llena en el
    # mismo formulario del despertar.
    celular_fuera: Mapped[bool | None] = mapped_column(Boolean)
    origen: Mapped[OrigenDato] = mapped_column(
        Enum(OrigenDato, name="origen_dato"),
        nullable=False,
        server_default=OrigenDato.manual.value,
    )

    # REGLAS_NEGOCIO §6. Restar dos timestamptz da un interval, y
    # EXTRACT(EPOCH FROM interval) es IMMUTABLE: se puede usar en una generada.
    horas_sueno: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        Computed("EXTRACT(EPOCH FROM (fin - inicio)) / 3600.0", persisted=True),
    )
