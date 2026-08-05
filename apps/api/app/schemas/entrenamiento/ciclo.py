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


class CicloRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    numero: int
    objetivo: str
    fecha_inicio: date
    semanas: int
    estado: EstadoCiclo


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
