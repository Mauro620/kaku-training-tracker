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
from app.models.types import Distancia, IntPk, Peso, UsuarioFk


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
        CheckConstraint(
            "dia_sugerido IS NULL OR dia_sugerido BETWEEN 0 AND 6",
            name="dia_sugerido_rango",
        ),
    )

    id: Mapped[IntPk]
    usuario_id: Mapped[UsuarioFk]
    ciclo_semana_id: Mapped[int | None] = mapped_column(ForeignKey("ciclo_semana.id"))
    # Nullable desde que el cumplimiento se mide por composición semanal, no
    # por fecha exacta (REGLAS_NEGOCIO §13). dia_sugerido (0=lunes..6=domingo)
    # es sugerencia de UI, no compromiso.
    fecha_prevista: Mapped[date | None] = mapped_column(Date)
    dia_sugerido: Mapped[int | None] = mapped_column(SmallInteger)
    tipo_sesion_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_sesion.id"), nullable=False
    )
    objetivo: Mapped[str | None] = mapped_column(Text)
    duracion_min_est: Mapped[int | None] = mapped_column(SmallInteger)
    rpe_objetivo: Mapped[int | None] = mapped_column(SmallInteger)

    bloques_planeados: Mapped[list["BloquePlan"]] = relationship(
        back_populates="sesion_plan", order_by="BloquePlan.orden"
    )


class BloquePlan(Base):
    """Objetivo del bloque real (antes `serie_plan`, REGLAS_NEGOCIO §15).
    Sin `calidad_objetivo`: la calidad es una medida de ejecución real, no
    algo que se planifique de antemano."""

    __tablename__ = "bloque_plan"
    __table_args__ = (
        UniqueConstraint("sesion_plan_id", "orden"),
        CheckConstraint("series IS NULL OR series > 0", name="series_positivas"),
        CheckConstraint(
            "reps_min IS NULL OR reps_max IS NULL OR reps_min <= reps_max",
            name="reps_ordenadas",
        ),
        CheckConstraint(
            "distancia_objetivo_m IS NULL OR distancia_objetivo_m > 0",
            name="distancia_objetivo_m_positiva",
        ),
        CheckConstraint(
            "duracion_objetivo_s IS NULL OR duracion_objetivo_s > 0",
            name="duracion_objetivo_s_positiva",
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
    series: Mapped[int | None] = mapped_column(SmallInteger)
    reps_min: Mapped[int | None] = mapped_column(SmallInteger)
    reps_max: Mapped[int | None] = mapped_column(SmallInteger)
    peso_objetivo_kg: Mapped[Peso | None]
    distancia_objetivo_m: Mapped[Distancia | None]
    duracion_objetivo_s: Mapped[int | None] = mapped_column(SmallInteger)

    sesion_plan: Mapped[SesionPlan] = relationship(back_populates="bloques_planeados")
