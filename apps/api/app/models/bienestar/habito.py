import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import IntPk, UsuarioFk


class Habito(Base):
    """Tabla, no columnas. Agregar un hábito es un INSERT, no una migración."""

    __tablename__ = "habito"
    __table_args__ = (UniqueConstraint("usuario_id", "nombre"),)

    id: Mapped[IntPk]
    usuario_id: Mapped[UsuarioFk]
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")

    registros: Mapped[list["HabitoRegistro"]] = relationship(back_populates="habito")


class HabitoRegistro(Base):
    """PK compuesta `(habito_id, fecha)`: un hábito tiene como máximo un
    registro por día.

    `idempotency_key` es metadata para la cola de Fase 5: la deduplicacion
    real sigue siendo la PK compuesta. Nullable para admitir backfill
    historico (Fase 9, Notion).
    """

    __tablename__ = "habito_registro"

    habito_id: Mapped[int] = mapped_column(ForeignKey("habito.id"), primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    valor: Mapped[bool] = mapped_column(Boolean, nullable=False)
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)

    habito: Mapped[Habito] = relationship(back_populates="registros")
