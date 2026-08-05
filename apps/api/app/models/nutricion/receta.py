from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MomentoComida
from app.models.types import Gramos, IntPk, UsuarioFk


class Receta(Base):
    """Se calibra una vez, después registrar es un tap.

    Los macros son derivados (`REGLAS_NEGOCIO §12`), no se almacenan: guardar
    un total calculado es garantizar que quede desactualizado el día que se
    corrija un alimento.
    """

    __tablename__ = "receta"
    __table_args__ = (UniqueConstraint("usuario_id", "nombre"),)

    id: Mapped[IntPk]
    usuario_id: Mapped[UsuarioFk]
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    momento_default: Mapped[MomentoComida | None] = mapped_column(
        Enum(MomentoComida, name="momento_comida")
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    items: Mapped[list["RecetaItem"]] = relationship(back_populates="receta")


class RecetaItem(Base):
    __tablename__ = "receta_item"
    __table_args__ = (
        UniqueConstraint("receta_id", "alimento_id"),
        CheckConstraint("cantidad_g > 0", name="cantidad_g_positiva"),
    )

    id: Mapped[IntPk]
    receta_id: Mapped[int] = mapped_column(ForeignKey("receta.id"), nullable=False)
    alimento_id: Mapped[int] = mapped_column(ForeignKey("alimento.id"), nullable=False)
    cantidad_g: Mapped[Gramos] = mapped_column(nullable=False)

    receta: Mapped[Receta] = relationship(back_populates="items")
