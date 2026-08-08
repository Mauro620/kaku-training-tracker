"""Schemas para la pantalla 'Esta semana' (C de la revision de UI).

El backend devuelve la data cruda por dia, la UI calcula el flag
cumplido/incumplido/sin-dato por dimension. Asi la logica de
cumplimiento (cambiar '>= objetivo' por '>= 80% del objetivo', por
ejemplo) vive en el cliente, donde es mas facil iterar.
"""

from datetime import date
from decimal import Decimal

from pydantic import ConfigDict

from app.schemas.base import ReadBase, SchemaBase


class SuenoDiaSchema(ReadBase):
    """null = no hay registro de sueno ese dia. horas = 0 si no hay."""

    model_config = ConfigDict(from_attributes=True)

    horas: Decimal | None
    objetivo_h: Decimal


class SesionDiaSchema(ReadBase):
    """True si hay al menos una sesion de cualquier tipo ese dia. La
    composicion de la sesion (fuerza, velocidad, etc.) vive en la
    pestana Entreno (no aca)."""

    registrada: bool


class HidratacionDiaSchema(ReadBase):
    """null = no hay registro de hidratacion ese dia."""

    model_config = ConfigDict(from_attributes=True)

    ml_totales: int | None
    objetivo_ml: int


class HabitosDiaSchema(ReadBase):
    """marcados cuenta los True de la fecha. activos es el total de
    habitos activos del usuario (constante para todos los dias del
    rango, pero la repetimos por dia para que la UI no haga otro
    fetch)."""

    marcados: int
    activos: int


class BienestarDiaSchema(ReadBase):
    """True si el usuario completo los 4 sliders de Hooper ese dia."""

    registrado: bool


class DiaCierreSchema(ReadBase):
    """Una unidad minima: los datos crudos de las 5 dimensiones para
    un dia. La UI deriva las flags cumplidas y las pinta."""

    fecha: date
    sueno: SuenoDiaSchema
    sesion: SesionDiaSchema
    hidratacion: HidratacionDiaSchema
    habitos: HabitosDiaSchema
    bienestar: BienestarDiaSchema


class CierreSemanaRead(SchemaBase):
    """Una lista de 7 dias (o N si el caller pide mas). El cliente
    decide el tamano del rango."""

    dias: list[DiaCierreSchema]
