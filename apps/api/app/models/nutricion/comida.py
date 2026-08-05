import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MomentoComida
from app.models.types import BigIntPk, Gramos, IdempotencyKey, UsuarioFk, UuidPk


class ComidaLog(Base):
    """`receta_id` nulo = comida improvisada, y sus ingredientes van en
    `comida_item`. Si hay receta, los ingredientes se resuelven vía
    `receta_item` y no se duplican acá."""

    __tablename__ = "comida_log"
    __table_args__ = (
        Index(
            "ix_comida_log_usuario_id_fecha_momento", "usuario_id", "fecha", "momento"
        ),
    )

    id: Mapped[UuidPk]
    usuario_id: Mapped[UsuarioFk]
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    momento: Mapped[MomentoComida] = mapped_column(
        Enum(MomentoComida, name="momento_comida"), nullable=False
    )
    receta_id: Mapped[int | None] = mapped_column(ForeignKey("receta.id"))
    nota: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[IdempotencyKey]

    items: Mapped[list["ComidaItem"]] = relationship(back_populates="comida_log")


class ComidaItem(Base):
    """Solo para comidas sin receta. Evita duplicar la despensa en cada
    registro."""

    __tablename__ = "comida_item"
    __table_args__ = (CheckConstraint("cantidad_g > 0", name="cantidad_g_positiva"),)

    id: Mapped[BigIntPk]
    comida_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comida_log.id"), nullable=False
    )
    alimento_id: Mapped[int] = mapped_column(ForeignKey("alimento.id"), nullable=False)
    cantidad_g: Mapped[Gramos] = mapped_column(nullable=False)

    comida_log: Mapped[ComidaLog] = relationship(back_populates="items")
