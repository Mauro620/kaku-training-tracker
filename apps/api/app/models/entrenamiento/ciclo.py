from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EstadoCiclo, FaseCiclo
from app.models.types import IntPk, UsuarioFk


class Ciclo(Base):
    __tablename__ = "ciclo"
    __table_args__ = (UniqueConstraint("usuario_id", "numero"),)

    id: Mapped[IntPk]
    usuario_id: Mapped[UsuarioFk]
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    objetivo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    semanas: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="4"
    )
    estado: Mapped[EstadoCiclo] = mapped_column(
        Enum(EstadoCiclo, name="estado_ciclo"),
        nullable=False,
        server_default=EstadoCiclo.planificado.value,
    )

    semanas_del_ciclo: Mapped[list["CicloSemana"]] = relationship(
        back_populates="ciclo", order_by="CicloSemana.numero"
    )


class CicloSemana(Base):
    """Los RPE objetivo viven acá y no en `parametro`: varían por fase del
    ciclo, así que no son un umbral global."""

    __tablename__ = "ciclo_semana"
    __table_args__ = (
        UniqueConstraint("ciclo_id", "numero"),
        CheckConstraint(
            "rpe_objetivo_min IS NULL OR rpe_objetivo_min BETWEEN 1 AND 10",
            name="rpe_objetivo_min_rango",
        ),
        CheckConstraint(
            "rpe_objetivo_max IS NULL OR rpe_objetivo_max BETWEEN 1 AND 10",
            name="rpe_objetivo_max_rango",
        ),
        CheckConstraint(
            "rpe_objetivo_min IS NULL "
            "OR rpe_objetivo_max IS NULL "
            "OR rpe_objetivo_min <= rpe_objetivo_max",
            name="rpe_objetivo_ordenado",
        ),
    )

    id: Mapped[IntPk]
    ciclo_id: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), nullable=False)
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fase: Mapped[FaseCiclo] = mapped_column(
        Enum(FaseCiclo, name="fase_ciclo"), nullable=False
    )
    rpe_objetivo_min: Mapped[int | None] = mapped_column(SmallInteger)
    rpe_objetivo_max: Mapped[int | None] = mapped_column(SmallInteger)
    volumen_pct: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="100"
    )

    ciclo: Mapped[Ciclo] = relationship(back_populates="semanas_del_ciclo")
