import uuid
from datetime import date
from typing import Self

from pydantic import model_validator

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import DuracionMin, NoNegativo, Peso, Positivo, Rpe


class SesionPlanCreate(SchemaBase):
    ciclo_semana_id: int | None = None
    fecha_prevista: date
    tipo_sesion_id: int
    objetivo: str | None = None
    duracion_min_est: DuracionMin | None = None
    rpe_objetivo: Rpe | None = None


class SesionPlanUpdate(SchemaBase):
    ciclo_semana_id: int | None = None
    fecha_prevista: date | None = None
    tipo_sesion_id: int | None = None
    objetivo: str | None = None
    duracion_min_est: DuracionMin | None = None
    rpe_objetivo: Rpe | None = None


class SesionPlanRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    ciclo_semana_id: int | None
    fecha_prevista: date
    tipo_sesion_id: int
    objetivo: str | None
    duracion_min_est: int | None
    rpe_objetivo: int | None


class _RepsOrdenadas(SchemaBase):
    reps_min: Positivo | None = None
    reps_max: Positivo | None = None

    @model_validator(mode="after")
    def _validar_orden(self) -> Self:
        minimo, maximo = self.reps_min, self.reps_max
        if minimo is not None and maximo is not None and minimo > maximo:
            raise ValueError("reps_min no puede superar a reps_max")
        return self


class SeriePlanCreate(_RepsOrdenadas):
    sesion_plan_id: int
    ejercicio_id: int
    orden: NoNegativo
    series: Positivo
    peso_objetivo_kg: Peso | None = None


class SeriePlanUpdate(_RepsOrdenadas):
    ejercicio_id: int | None = None
    orden: NoNegativo | None = None
    series: Positivo | None = None
    peso_objetivo_kg: Peso | None = None


class SeriePlanRead(ReadBase):
    id: int
    sesion_plan_id: int
    ejercicio_id: int
    orden: int
    series: int
    reps_min: int | None
    reps_max: int | None
    peso_objetivo_kg: Peso | None
