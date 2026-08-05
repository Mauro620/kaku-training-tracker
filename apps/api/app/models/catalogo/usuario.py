from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Peso, UuidPk


class Usuario(Base):
    """App de un solo usuario hoy.

    La FK existe en el resto de las tablas para no migrar 20 tablas si mañana
    entra un compañero o un preparador. Los umbrales calibrables (objetivo de
    sueño, proteína por kg) NO viven acá: viven en `parametro`, que es el único
    lugar calibrable. Tenerlos en dos lados garantiza que un día no coincidan.

    `agua_objetivo_ml_min/max` SÍ vive acá, como `peso_objetivo_kg`: es una
    meta personal directa, no una constante de fórmula compartida.
    """

    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(
            "agua_objetivo_ml_min IS NULL OR agua_objetivo_ml_max IS NULL "
            "OR agua_objetivo_ml_min <= agua_objetivo_ml_max",
            name="agua_objetivo_ml_ordenado",
        ),
    )

    id: Mapped[UuidPk]
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    peso_objetivo_kg: Mapped[Peso | None]
    agua_objetivo_ml_min: Mapped[int | None] = mapped_column(Integer)
    agua_objetivo_ml_max: Mapped[int | None] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
