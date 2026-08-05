from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import SmallIntPk


class Parametro(Base):
    """Umbrales y constantes de negocio, leídos en runtime.

    Ningún servicio recibe un umbral como literal. Si aparece un `1.3` o un
    `7.0` dentro de una función, la clave que falta va acá.

    La unicidad es `(clave, vigente_desde)` y no `clave` sola: así un parámetro
    puede tener varias versiones en el tiempo. La lectura toma siempre la fila
    con el mayor `vigente_desde <= CURRENT_DATE`. Recalcular el histórico con
    los umbrales de hoy destruiría la trazabilidad de por qué el Estado dio lo
    que dio en su momento.
    """

    __tablename__ = "parametro"
    __table_args__ = (UniqueConstraint("clave", "vigente_desde"),)

    id: Mapped[SmallIntPk]
    clave: Mapped[str] = mapped_column(String(60), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    unidad: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    vigente_desde: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=text("CURRENT_DATE")
    )
