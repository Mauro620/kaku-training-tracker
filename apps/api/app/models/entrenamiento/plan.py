from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import IntPk, Peso, UsuarioFk


class SesionPlan(Base):
    """El plan se registra ANTES. El delta contra la sesión real es la señal
    de fatiga: sin plan previo no hay contra qué comparar."""

    __tablename__ = "sesion_plan"
    __table_args__ = (
        CheckConstraint(
            "rpe_objetivo IS NULL OR rpe_objetivo BETWEEN 1 AND 10",
            name="rpe_objetivo_rango",
        ),
        CheckConstraint(
            "duracion_min_est IS NULL OR duracion_min_est > 0",
            name="duracion_min_est_positiva",
        ),
    )

    id: Mapped[IntPk]
    usuario_id: Mapped[UsuarioFk]
    ciclo_semana_id: Mapped[int | None] = mapped_column(ForeignKey("ciclo_semana.id"))
    fecha_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_sesion_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_sesion.id"), nullable=False
    )
    objetivo: Mapped[str | None] = mapped_column(Text)
    duracion_min_est: Mapped[int | None] = mapped_column(SmallInteger)
    rpe_objetivo: Mapped[int | None] = mapped_column(SmallInteger)

    series_planeadas: Mapped[list["SeriePlan"]] = relationship(
        back_populates="sesion_plan", order_by="SeriePlan.orden"
    )


class SeriePlan(Base):
    __tablename__ = "serie_plan"
    __table_args__ = (
        UniqueConstraint("sesion_plan_id", "orden"),
        CheckConstraint("series > 0", name="series_positivas"),
        CheckConstraint(
            "reps_min IS NULL OR reps_max IS NULL OR reps_min <= reps_max",
            name="reps_ordenadas",
        ),
    )

    id: Mapped[IntPk]
    sesion_plan_id: Mapped[int] = mapped_column(
        ForeignKey("sesion_plan.id"), nullable=False
    )
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicio.id"), nullable=False
    )
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    series: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reps_min: Mapped[int | None] = mapped_column(SmallInteger)
    reps_max: Mapped[int | None] = mapped_column(SmallInteger)
    peso_objetivo_kg: Mapped[Peso | None]

    sesion_plan: Mapped[SesionPlan] = relationship(back_populates="series_planeadas")
