import uuid
from datetime import date
from typing import Self

from pydantic import Field, model_validator

from app.models.enums import EstadoCiclo, FaseCiclo
from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import Positivo, Rpe


class CicloCreate(SchemaBase):
    numero: Positivo
    objetivo: str = Field(min_length=1)
    fecha_inicio: date
    semanas: Positivo = 4
    estado: EstadoCiclo = EstadoCiclo.planificado


class CicloUpdate(SchemaBase):
    objetivo: str | None = Field(default=None, min_length=1)
    fecha_inicio: date | None = None
    semanas: Positivo | None = None
    estado: EstadoCiclo | None = None


class CicloCerrarRequest(SchemaBase):
    """Sin body obligatorio: `fecha_cierre_real` default hoy. El service
    setea `estado=cerrado` junto con la fecha, atómico — el cliente no
    tiene que conocer el CHECK que los mantiene coherentes."""

    fecha_cierre_real: date | None = None


class CicloRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    numero: int
    objetivo: str
    fecha_inicio: date
    semanas: int
    estado: EstadoCiclo
    fecha_fin_prevista: date
    fecha_cierre_real: date | None


class _RpeObjetivoOrdenado(SchemaBase):
    rpe_objetivo_min: Rpe | None = None
    rpe_objetivo_max: Rpe | None = None

    @model_validator(mode="after")
    def _validar_orden(self) -> Self:
        minimo, maximo = self.rpe_objetivo_min, self.rpe_objetivo_max
        if minimo is not None and maximo is not None and minimo > maximo:
            raise ValueError("rpe_objetivo_min no puede superar a rpe_objetivo_max")
        return self


class CicloSemanaCreate(_RpeObjetivoOrdenado):
    ciclo_id: int
    numero: Positivo
    fase: FaseCiclo
    volumen_pct: Positivo = 100


class CicloSemanaUpdate(_RpeObjetivoOrdenado):
    fase: FaseCiclo | None = None
    volumen_pct: Positivo | None = None


class CicloSemanaRead(ReadBase):
    id: int
    ciclo_id: int
    numero: int
    fase: FaseCiclo
    rpe_objetivo_min: int | None
    rpe_objetivo_max: int | None
    volumen_pct: int


class ComposicionItem(SchemaBase):
    """Un tipo de sesión con su cantidad objetivo en la semana."""

    tipo_sesion_id: int
    cantidad_objetivo: Positivo


class ReemplazarComposicionRequest(SchemaBase):
    """Reemplaza TODA la composición de la semana (no upsert incremental):
    declarar la semana completa de una vez evita composiciones a medias
    con filas viejas colgando."""

    items: list[ComposicionItem] = Field(min_length=1)


class ComposicionItemRead(ReadBase):
    tipo_sesion_id: int
    cantidad_objetivo: int


class CumplimientoItem(ReadBase):
    tipo_sesion_id: int
    tipo_sesion_codigo: str
    tipo_sesion_nombre: str
    objetivo: int
    hecho: int
    cumplido: bool
