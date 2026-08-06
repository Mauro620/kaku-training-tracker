from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Computed,
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
    __table_args__ = (
        UniqueConstraint("usuario_id", "numero"),
        CheckConstraint(
            "fecha_cierre_real IS NULL OR estado = 'cerrado'",
            name="fecha_cierre_coherente",
        ),
    )

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
    # Derivada, nunca se captura: fecha_inicio + (semanas x 7 - 1) dias.
    fecha_fin_prevista: Mapped[date] = mapped_column(
        Date,
        Computed("fecha_inicio + (semanas * 7 - 1)", persisted=True),
    )
    # NULL hasta que el ciclo se cierra. La distancia contra
    # fecha_fin_prevista es la señal de "se cortó antes/después de lo
    # planeado" (REGLAS_NEGOCIO, docs/PENDIENTES.md).
    fecha_cierre_real: Mapped[date | None] = mapped_column(Date)

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


class CicloSemanaComposicion(Base):
    """Composición objetivo de la semana por tipo de sesión (ej. fuerza: 2).

    Cuelga de `ciclo_semana`, no de `ciclo`: la semana de descarga puede
    llevar 1 de fuerza en vez de 2 sin lógica especial, cada semana declara
    la suya (REGLAS_NEGOCIO §13)."""

    __tablename__ = "ciclo_semana_composicion"
    __table_args__ = (
        UniqueConstraint("ciclo_semana_id", "tipo_sesion_id"),
        CheckConstraint("cantidad_objetivo > 0", name="cantidad_objetivo_positiva"),
    )

    id: Mapped[IntPk]
    ciclo_semana_id: Mapped[int] = mapped_column(
        ForeignKey("ciclo_semana.id"), nullable=False
    )
    tipo_sesion_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_sesion.id"), nullable=False
    )
    cantidad_objetivo: Mapped[int] = mapped_column(SmallInteger, nullable=False)
