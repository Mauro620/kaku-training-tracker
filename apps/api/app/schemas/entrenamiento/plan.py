import uuid
from datetime import date
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import (
    DiaSemana,
    Distancia,
    DuracionMin,
    DuracionSeg,
    NoNegativo,
    Peso,
    Positivo,
    Rpe,
)


class SesionPlanCreate(SchemaBase):
    """`dia_sugerido` (0=lunes..6=domingo) es sugerencia de UI, no
    compromiso: si se envía, el service valida el espaciado (REGLAS_NEGOCIO
    §13.3) contra sesiones reales y otros planes del mismo ciclo."""

    ciclo_semana_id: int | None = None
    fecha_prevista: date | None = None
    dia_sugerido: DiaSemana | None = None
    tipo_sesion_id: int
    objetivo: str | None = None
    duracion_min_est: DuracionMin | None = None
    rpe_objetivo: Rpe | None = None
    # Bloques objetivo en el mismo body, igual que sesion/bloque: si se
    # mandan, se crean con el `sesion_plan_id` que el server acaba de asignar.
    bloques: list["BloquePlanSinPlanCreate"] | None = None


class SesionPlanUpdate(SchemaBase):
    ciclo_semana_id: int | None = None
    fecha_prevista: date | None = None
    dia_sugerido: DiaSemana | None = None
    tipo_sesion_id: int | None = None
    objetivo: str | None = None
    duracion_min_est: DuracionMin | None = None
    rpe_objetivo: Rpe | None = None


class SesionPlanRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    ciclo_semana_id: int | None
    fecha_prevista: date | None
    dia_sugerido: int | None
    tipo_sesion_id: int
    objetivo: str | None
    duracion_min_est: int | None
    rpe_objetivo: int | None
    bloques_planeados: list["BloquePlanRead"] = Field(default_factory=list)


class _RepsOrdenadas(SchemaBase):
    reps_min: Positivo | None = None
    reps_max: Positivo | None = None

    @model_validator(mode="after")
    def _validar_orden(self) -> Self:
        minimo, maximo = self.reps_min, self.reps_max
        if minimo is not None and maximo is not None and minimo > maximo:
            raise ValueError("reps_min no puede superar a reps_max")
        return self


class BloquePlanCreate(_RepsOrdenadas):
    """Objetivo del bloque real (REGLAS_NEGOCIO §15). Sin `calidad`: no se
    planifica de antemano, es una medida de ejecución."""

    sesion_plan_id: int
    ejercicio_id: int
    orden: NoNegativo
    series: Positivo | None = None
    peso_objetivo_kg: Peso | None = None
    distancia_objetivo_m: Distancia | None = None
    duracion_objetivo_s: DuracionSeg | None = None


class BloquePlanSinPlanCreate(_RepsOrdenadas):
    """Un bloque objetivo dentro del body de POST /planes: el
    `sesion_plan_id` lo completa el server con el id del plan recien creado."""

    ejercicio_id: int
    orden: NoNegativo
    series: Positivo | None = None
    peso_objetivo_kg: Peso | None = None
    distancia_objetivo_m: Distancia | None = None
    duracion_objetivo_s: DuracionSeg | None = None


class BloquePlanUpdate(_RepsOrdenadas):
    ejercicio_id: int | None = None
    orden: NoNegativo | None = None
    series: Positivo | None = None
    peso_objetivo_kg: Peso | None = None
    distancia_objetivo_m: Distancia | None = None
    duracion_objetivo_s: DuracionSeg | None = None


class BloquePlanRead(ReadBase):
    id: int
    sesion_plan_id: int
    ejercicio_id: int
    orden: int
    series: int | None
    reps_min: int | None
    reps_max: int | None
    peso_objetivo_kg: Peso | None
    distancia_objetivo_m: Distancia | None
    duracion_objetivo_s: int | None


# Resuelve las forward refs.
SesionPlanCreate.model_rebuild()
SesionPlanRead.model_rebuild()
