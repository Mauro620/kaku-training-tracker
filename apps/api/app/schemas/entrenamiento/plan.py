import uuid
from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import Field, model_validator

from app.models.enums import EstadoSesionPlan, FaseCiclo
from app.schemas.base import ReadBase, SchemaBase
from app.schemas.entrenamiento.sesion import BloqueEjercicioEnDetalleRead
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
    estado: EstadoSesionPlan
    # NULL en los planes creados a mano: solo el importador la asigna.
    clave_import: str | None
    # Etiqueta legible y contexto de la semana (docs/PLAN_IMPORT.md §2.3).
    nombre: str | None
    nota: str | None
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
    # DE ESTA VEZ (§15). Se precarga hacia bloque.nota al registrar.
    nota: str | None


# Resuelve las forward refs.
SesionPlanCreate.model_rebuild()
SesionPlanRead.model_rebuild()


# ============================================================== detalle (R9) ==.
#
# Schemas para `GET /planes/{id}` (SPEC §3.8): la forma de plan que consume la
# pantalla previa a ejecutar. Es el shape completo, con sus bloques planeados
# y su ciclo anidados — más rico que el subset `PlanDetalleEnSesionRead` que
# cuelga del detalle de sesión (R8.1).


class PlanCicloRead(ReadBase):
    """Ciclo + semana del plan anidado en `PlanDetalleRead`.

    `numero` y `semana` son los identificadores humanos; `fase` es la clave
    para pintar la banda de carga del plan. Distinto del `PlanCicloRead`
    declarado en `sesion.py`: el subset del detalle de sesión incluye
    también `objetivo` del ciclo y no incluye `numero` ni `semana` como
    campos separados (porque ya los conoce por contexto)."""

    numero: int
    semana: int
    fase: FaseCiclo


class PlanDetalleRead(ReadBase):
    """Plan completo con su ciclo y sus bloques planeados. Salida del
    endpoint `GET /planes/{id}` (SPEC §3.8).

    El campo `bloques_planeados` ya viene ordenado por `orden` ASC (el
    modelo `SesionPlan.bloques_planeados` lo declara). `ciclo` es opcional
    porque la FK a `ciclo_semana.id` es nullable: un plan creado a mano
    puede no colgar de ningún ciclo.
    """

    id: int
    usuario_id: uuid.UUID
    ciclo_semana_id: int | None
    ciclo: PlanCicloRead | None
    fecha_prevista: date | None
    dia_sugerido: int | None
    tipo_sesion_id: int
    objetivo: str | None
    duracion_min_est: int | None
    rpe_objetivo: int | None
    estado: EstadoSesionPlan
    clave_import: str | None
    nombre: str | None
    nota: str | None
    bloques_planeados: list["BloquePlanDetalleRead"] = Field(default_factory=list)


class BloquePlanDetalleRead(ReadBase):
    """Cada bloque planeado con su ejercicio anidado.

    Reusa `BloqueEjercicioEnDetalleRead` (subset de `EjercicioRead` ya
    introducido en R8.1) en vez de declarar un schema propio: el detalle
    de plan y el detalle de sesión exponen la misma forma de ejercicio.
    """

    id: int
    sesion_plan_id: int
    orden: int
    series: int | None
    reps_min: int | None
    reps_max: int | None
    peso_objetivo_kg: Decimal | None
    distancia_objetivo_m: Decimal | None
    duracion_objetivo_s: int | None
    nota: str | None
    ejercicio: BloqueEjercicioEnDetalleRead


# Resuelve la forward ref de PlanDetalleRead.bloques_planeados.
PlanDetalleRead.model_rebuild()
