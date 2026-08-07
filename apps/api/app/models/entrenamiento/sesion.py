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
from app.models.types import (
    BigIntPk,
    Distancia,
    IdempotencyKey,
    Peso,
    UsuarioFk,
    UuidPk,
)


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

    # passive_deletes="all": al borrar la sesion, confia en el ON DELETE
    # CASCADE de la FK en vez de que el ORM intente poner sesion_id=NULL en
    # cada bloque antes (fallaria: la columna es NOT NULL). "all" en vez de
    # True: la coleccion suele venir precargada via selectinload
    # (obtener_sesion), y solo "all" desactiva la sincronizacion tambien
    # para colecciones ya cargadas, no solo las lazy.
    bloques: Mapped[list["Bloque"]] = relationship(
        back_populates="sesion", order_by="Bloque.orden", passive_deletes="all"
    )
    partido: Mapped["Partido | None"] = relationship(back_populates="sesion")


class Bloque(Base):
    """Antes `serie`: "N series x M reps" no describe un sprint ni un
    control tecnico. Que campos aplican los determina
    `ejercicio.tipo_medicion`, validado en el service (REGLAS_NEGOCIO §15)."""

    __tablename__ = "bloque"
    __table_args__ = (
        UniqueConstraint("sesion_id", "orden"),
        CheckConstraint("rpe IS NULL OR rpe BETWEEN 1 AND 10", name="rpe_rango"),
        CheckConstraint("series IS NULL OR series > 0", name="series_positivas"),
        CheckConstraint("reps IS NULL OR reps > 0", name="reps_positivas"),
        CheckConstraint(
            "distancia_m IS NULL OR distancia_m > 0", name="distancia_m_positiva"
        ),
        CheckConstraint(
            "duracion_s IS NULL OR duracion_s > 0", name="duracion_s_positiva"
        ),
        CheckConstraint(
            "calidad IS NULL OR calidad BETWEEN 1 AND 5", name="calidad_rango"
        ),
    )

    id: Mapped[BigIntPk]
    # ondelete=CASCADE: borrar una sesion borra sus bloques con ella, no
    # tienen existencia propia sin la sesion (eliminar sesion, ROADMAP §4).
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sesion.id", ondelete="CASCADE"), nullable=False
    )
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicio.id"), nullable=False
    )
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    series: Mapped[int | None] = mapped_column(SmallInteger)
    reps: Mapped[int | None] = mapped_column(SmallInteger)
    distancia_m: Mapped[Distancia | None]
    duracion_s: Mapped[int | None] = mapped_column(Integer)
    calidad: Mapped[int | None] = mapped_column(SmallInteger)
    peso_kg: Mapped[Peso | None]
    rpe: Mapped[int | None] = mapped_column(SmallInteger)
    dolor_lumbar: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    sesion: Mapped[Sesion] = relationship(back_populates="bloques")


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


__all__ = ["Bloque", "Partido", "Sesion"]
