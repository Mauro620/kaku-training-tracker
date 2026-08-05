from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Peso, UuidPk


class Usuario(Base):
    """App de un solo usuario hoy.

    La FK existe en el resto de las tablas para no migrar 20 tablas si mañana
    entra un compañero o un preparador. Los umbrales calibrables (objetivo de
    sueño, proteína por kg) NO viven acá: viven en `parametro`, que es el único
    lugar calibrable. Tenerlos en dos lados garantiza que un día no coincidan.
    """

    __tablename__ = "usuario"

    id: Mapped[UuidPk]
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    peso_objetivo_kg: Mapped[Peso | None]
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
