"""Catálogos sembrados. Agregar una fila es un seed, nunca una migración."""

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CargaLumbar, Demanda, TipoMedicion
from app.models.types import IntPk, SmallIntPk


class TipoSesion(Base):
    __tablename__ = "tipo_sesion"

    id: Mapped[SmallIntPk]
    codigo: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    demanda: Mapped[Demanda] = mapped_column(
        Enum(Demanda, name="demanda"), nullable=False
    )


class Ejercicio(Base):
    __tablename__ = "ejercicio"

    id: Mapped[IntPk]
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    patron: Mapped[str | None] = mapped_column(String(40))
    # Permite filtrar alternativas seguras cuando la molestia lumbar está activa.
    carga_lumbar: Mapped[CargaLumbar] = mapped_column(
        Enum(CargaLumbar, name="carga_lumbar"),
        nullable=False,
        server_default=CargaLumbar.baja.value,
    )
    # Nullable: el ejercicio que el usuario crea inline (POST
    # /catalogos/ejercicios) solo pide nombre + tipo_medicion. Ya no filtra
    # el selector de ejercicio (eso lo decide tipo_medicion, REGLAS_NEGOCIO
    # §15) — queda como categorizacion de referencia.
    tipo_sesion_id: Mapped[int | None] = mapped_column(ForeignKey("tipo_sesion.id"))
    # Determina que campos acepta cada bloque de este ejercicio.
    tipo_medicion: Mapped[TipoMedicion] = mapped_column(
        Enum(TipoMedicion, name="tipo_medicion"), nullable=False
    )


class ZonaCorporal(Base):
    __tablename__ = "zona_corporal"

    id: Mapped[SmallIntPk]
    nombre: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)


class TipoTest(Base):
    __tablename__ = "tipo_test"

    id: Mapped[SmallIntPk]
    codigo: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    unidad: Mapped[str] = mapped_column(String(10), nullable=False)
    # Evita el bug clásico: en sprint_10m menos es mejor, en cmj más es mejor.
    # Sin este campo el cálculo de mejora se invierte en la mitad de los tests.
    mejor_es_mayor: Mapped[bool] = mapped_column(Boolean, nullable=False)
