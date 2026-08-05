from datetime import date

from sqlalchemy import CheckConstraint, Date, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import BigIntPk, UsuarioFk


class RegistroHidratacion(Base):
    """A diferencia de registro_sueno/registro_bienestar, cada registro SUMA a
    `ml_totales` en vez de reemplazarlo: un termo de 750ml es un tap, no la
    cantidad total del día."""

    __tablename__ = "registro_hidratacion"
    __table_args__ = (
        UniqueConstraint("usuario_id", "fecha"),
        CheckConstraint("ml_totales >= 0", name="ml_totales_no_negativos"),
    )

    id: Mapped[BigIntPk]
    usuario_id: Mapped[UsuarioFk]
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    ml_totales: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
