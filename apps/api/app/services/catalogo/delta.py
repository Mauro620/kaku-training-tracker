"""Calculo de delta plan vs real (SPEC §2.1).

Funciones puras: reciben dataclasses de input con los campos que
necesitan (no modelos de SQLAlchemy), no tocan la base, no leen
parametros. Eso deja el modulo facil de triangular y de testear.

Las funciones se mantienen deliberadamente sin estado: el service que
las usa es el que resuelve la sesion con su `sesion_plan` y le pasa
los pedazos que el delta necesita. Asi no tenemos un acoplamiento
estructural entre este modulo y el ORM.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

T = TypeVar("T", int, Decimal)


@dataclass(frozen=True)
class BloqueDeltaInput:
    """Lo que el usuario realmente hizo en el bloque."""

    series: int | None
    reps: int | None
    peso_kg: Decimal | None
    distancia_m: Decimal | None = None
    duracion_s: int | None = None


@dataclass(frozen=True)
class BloquePlanDeltaInput:
    """Lo que el plan decia. `reps_min` y `reps_max` pueden coincidir
    (rango de amplitud cero) cuando el LLM declaro un rep exacto."""

    series: int | None
    reps_min: int | None
    reps_max: int | None
    peso_objetivo_kg: Decimal | None
    distancia_objetivo_m: Decimal | None = None
    duracion_objetivo_s: int | None = None


@dataclass(frozen=True)
class SesionDeltaInput:
    duracion_min: int
    rpe: int
    carga_srpe: int


@dataclass(frozen=True)
class SesionPlanDeltaInput:
    duracion_min_est: int | None
    rpe_objetivo: int | None


@dataclass(frozen=True)
class BloqueDeltaResultado:
    series: int | None
    reps: int | None
    peso_kg: Decimal | None
    distancia_m: Decimal | None
    duracion_s: int | None


@dataclass(frozen=True)
class SesionDeltaResultado:
    duracion_min: int | None
    rpe: int | None
    carga_srpe: int | None


def _delta_simple(real: T | None, objetivo: T | None) -> T | None:
    """Resta clasica, NULL propagado: si el objetivo es NULL, el delta
    es NULL. Nunca se asume cero. Acepta `int` o `Decimal`: series,
    reps, duracion son enteros; peso y distancia son decimales."""
    if objetivo is None:
        return None
    if real is None:
        return None
    return real - objetivo


def _delta_reps(real: int | None, plan: BloquePlanDeltaInput) -> int | None:
    """Rangos de reps: se mide contra el limite mas cercano.
    Dentro del rango (incluido el caso rango cerrado min==max) el delta
    es cero. Fuera, se mide contra el limite violado."""
    if plan.reps_min is None or plan.reps_max is None:
        return None
    if real is None:
        return None
    if real < plan.reps_min:
        return real - plan.reps_min
    if real > plan.reps_max:
        return real - plan.reps_max
    return 0


def delta_bloque(
    real: BloqueDeltaInput, plan: BloquePlanDeltaInput | None
) -> BloqueDeltaResultado:
    """Calcula el delta de un bloque contra su plan, o todos NULL si
    no hay plan (bloque extra, sesion libre, etc.)."""
    if plan is None:
        return BloqueDeltaResultado(None, None, None, None, None)

    return BloqueDeltaResultado(
        series=_delta_simple(real.series, plan.series),
        reps=_delta_reps(real.reps, plan),
        peso_kg=_delta_simple(real.peso_kg, plan.peso_objetivo_kg),
        distancia_m=_delta_simple(real.distancia_m, plan.distancia_objetivo_m),
        duracion_s=_delta_simple(real.duracion_s, plan.duracion_objetivo_s),
    )


def delta_sesion(
    real: SesionDeltaInput, plan: SesionPlanDeltaInput | None
) -> SesionDeltaResultado | None:
    """Delta a nivel de sesion. Si la sesion no tiene plan devuelve
    None: el caller sabe que no hay nada que computar y omite el
    bloque entero del payload."""
    if plan is None:
        return None

    duracion = _delta_simple(real.duracion_min, plan.duracion_min_est)
    rpe = _delta_simple(real.rpe, plan.rpe_objetivo)

    # `carga_srpe` del plan es la multiplicacion de los dos parametros;
    # si falta cualquiera de los dos no se puede calcular el objetivo y
    # el delta es NULL.
    carga_objetivo: int | None
    if plan.duracion_min_est is None or plan.rpe_objetivo is None:
        carga_objetivo = None
    else:
        carga_objetivo = plan.duracion_min_est * plan.rpe_objetivo
    carga = _delta_simple(real.carga_srpe, carga_objetivo)

    return SesionDeltaResultado(
        duracion_min=duracion,
        rpe=rpe,
        carga_srpe=carga,
    )
