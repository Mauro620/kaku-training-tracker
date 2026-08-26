import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import BigIntPk, UsuarioFk

if TYPE_CHECKING:
    from app.models.catalogo.catalogos import ZonaCorporal


class Molestia(Base):
    """Sin molestia no hay fila. No se pregunta a diario.

    Se registra para tener historial, no para autodiagnosticarse.

    La unicidad natural es `(usuario_id, fecha, zona_id)`; `idempotency_key`
    es metadata para la cola de Fase 5. Nullable para admitir backfill
    historico (Fase 9, Notion).
    """

    __tablename__ = "molestia"
    __table_args__ = (
        UniqueConstraint("usuario_id", "fecha", "zona_id"),
        # Sirve la consulta de frecuencia por zona en 14 días
        # (REGLAS_NEGOCIO §10.3), que va de zona hacia atrás en el tiempo.
        Index("ix_molestia_usuario_id_zona_id_fecha", "usuario_id", "zona_id", "fecha"),
        # El 0 es imposible por definición: sin molestia no hay fila.
        CheckConstraint("intensidad BETWEEN 1 AND 10", name="intensidad_rango"),
    )

    id: Mapped[BigIntPk]
    usuario_id: Mapped[UsuarioFk]
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    zona_id: Mapped[int] = mapped_column(ForeignKey("zona_corporal.id"), nullable=False)
    intensidad: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    nota: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)
    # Cargado via selectinload(Molestia.zona) en
    # `listar_por_usuario_y_fecha` (R8.3): el detalle de sesion expone el
    # nombre de la zona, no el id.
    zona: Mapped["ZonaCorporal"] = relationship()
