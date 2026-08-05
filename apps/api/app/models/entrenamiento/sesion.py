import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import BigIntPk, IdempotencyKey, Peso, UsuarioFk, UuidPk


class Sesion(Base):
    __tablename__ = "sesion"
    __table_args__ = (
        Index("ix_sesion_usuario_id_fecha", "usuario_id", "fecha"),
        CheckConstraint("rpe BETWEEN 1 AND 10", name="rpe_rango"),
        CheckConstraint("duracion_min > 0", name="duracion_min_positiva"),
    )

    id: Mapped[UuidPk]
    usuario_id: Mapped[UsuarioFk]
    # Nullable y unique a la vez: Postgres permite múltiples NULL en un índice
    # único, así que las sesiones sin plan previo no chocan entre sí.
    sesion_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("sesion_plan.id"), unique=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_sesion_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_sesion.id"), nullable=False
    )
    duracion_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rpe: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    nota: Mapped[str | None] = mapped_column(Text)

    # carga_srpe = rpe * duracion_min (REGLAS_NEGOCIO §1). Nunca se captura.
    # Integer y no SmallInteger: 10 * 32767 desborda smallint.
    carga_srpe: Mapped[int] = mapped_column(
        Integer, Computed("rpe * duracion_min", persisted=True)
    )

    idempotency_key: Mapped[IdempotencyKey]
    registrado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    series: Mapped[list["Serie"]] = relationship(
        back_populates="sesion", order_by="Serie.orden"
    )
    partido: Mapped["Partido | None"] = relationship(back_populates="sesion")


class Serie(Base):
    __tablename__ = "serie"
    __table_args__ = (
        UniqueConstraint("sesion_id", "orden"),
        CheckConstraint("rpe IS NULL OR rpe BETWEEN 1 AND 10", name="rpe_rango"),
        CheckConstraint("series > 0", name="series_positivas"),
        CheckConstraint("reps > 0", name="reps_positivas"),
    )

    id: Mapped[BigIntPk]
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sesion.id"), nullable=False
    )
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicio.id"), nullable=False
    )
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    series: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    peso_kg: Mapped[Peso | None]
    rpe: Mapped[int | None] = mapped_column(SmallInteger)
    dolor_lumbar: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    sesion: Mapped[Sesion] = relationship(back_populates="series")


class Partido(Base):
    """Un partido ES una sesión: duración y RPE viven en `sesion`, no se
    duplican. `minutos_jugados` no es `sesion.duracion_min`: esta última
    incluye el calentamiento."""

    __tablename__ = "partido"
    __table_args__ = (
        CheckConstraint("minutos_jugados >= 0", name="minutos_jugados_no_negativos"),
        CheckConstraint("goles >= 0", name="goles_no_negativos"),
        CheckConstraint("asistencias >= 0", name="asistencias_no_negativas"),
    )

    id: Mapped[UuidPk]
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sesion.id"), nullable=False, unique=True
    )
    rival: Mapped[str | None] = mapped_column(String(80))
    formato: Mapped[str | None] = mapped_column(String(20))
    minutos_jugados: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    goles: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    asistencias: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    recuperaciones: Mapped[int | None] = mapped_column(SmallInteger)
    salio_bien: Mapped[str | None] = mapped_column(Text)
    a_ajustar: Mapped[str | None] = mapped_column(Text)

    sesion: Mapped[Sesion] = relationship(back_populates="partido")


__all__ = ["Partido", "Serie", "Sesion"]
