import uuid
from datetime import date
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import DiaSemana, DuracionMin, NoNegativo, Peso, Positivo, Rpe


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
    # Series objetivo en el mismo body, igual que sesion/serie: si se
    # mandan, se crean con el `sesion_plan_id` que el server acaba de asignar.
    series: list["SeriePlanSinPlanCreate"] | None = None


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
    series_planeadas: list["SeriePlanRead"] = Field(default_factory=list)


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


class SeriePlanSinPlanCreate(_RepsOrdenadas):
    """Una serie objetivo dentro del body de POST /planes: el
    `sesion_plan_id` lo completa el server con el id del plan recien creado."""

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


# Resuelve las forward refs.
SesionPlanCreate.model_rebuild()
SesionPlanRead.model_rebuild()
