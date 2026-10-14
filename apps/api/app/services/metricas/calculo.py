"""Cálculo puro de las métricas de ciclo (REGLAS_NEGOCIO §17).

Sin acceso a la base: recibe listas y devuelve números, para que los casos de
REGLAS_NEGOCIO se prueben tal cual (AGENTS.md §3.5). El redondeo ocurre acá,
al serializar (§14): 1 decimal para porcentajes, horas y promedios.
"""

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal


def redondear(valor: float | Decimal, decimales: int = 1) -> float:
    return round(float(valor), decimales)


def porcentaje(parte: int, total: int) -> float | None:
    """`parte` / `total` x 100. NULL si el total es 0: sin denominador no hay
    porcentaje, y 0 % sería una afirmación falsa."""
    if total <= 0:
        return None
    return redondear(100 * parte / total)


def pct_ejecutado(
    *, cumplido: int, movido: int, descartado: int, planeadas: int
) -> float | None:
    """(cumplido + movido) / (planeadas - descartado) x 100. `movido` cuenta
    como ejecutado y `descartado` sale del denominador (REGLAS_NEGOCIO §17)."""
    return porcentaje(cumplido + movido, planeadas - descartado)


def promedio(valores: Iterable[float | Decimal | int]) -> float | None:
    """Promedio a 1 decimal; NULL si no hay datos (nunca 0, §14)."""
    lista = [float(v) for v in valores]
    if not lista:
        return None
    return redondear(sum(lista) / len(lista))


def carga_planeada(pares: Sequence[tuple[int | None, int | None]]) -> int:
    """Suma de rpe_objetivo x duracion_min_est de los planes que tienen los dos
    campos. Un plan sin alguno de los dos no aporta carga: no hay forma de
    estimarla sin inventar el dato que falta."""
    return sum(rpe * dur for rpe, dur in pares if rpe is not None and dur is not None)


def e1rm_epley(peso_kg: Decimal, reps: int, *, divisor: Decimal) -> Decimal:
    """1RM estimado (REGLAS_NEGOCIO §18.2): peso x (1 + reps / divisor). Con una
    sola repeticion el peso ya ES el maximo y no se infla."""
    if reps <= 1:
        return peso_kg
    return peso_kg * (1 + Decimal(reps) / divisor)


def calcular_acwr(
    carga_diaria: Mapping[date, int],
    fin: date,
    primera_fecha: date | None,
    *,
    dias_agudo: int,
    dias_cronico: int,
) -> float | None:
    """ACWR al dia `fin` (REGLAS_NEGOCIO §3).

    carga_aguda   = suma de los ultimos `dias_agudo` dias (incluye `fin`)
    carga_cronica = suma de los ultimos `dias_cronico` dias / (cronico / agudo)
    acwr          = aguda / cronica

    NULL con menos de `dias_cronico` dias de historia (contados desde
    `primera_fecha`, la primera sesion registrada) o con carga cronica 0. No se
    aproxima. Los dias sin sesion valen 0 y cuentan.
    """
    if primera_fecha is None or (fin - primera_fecha).days + 1 < dias_cronico:
        return None

    def suma(dias: int) -> int:
        return sum(carga_diaria.get(fin - timedelta(days=k), 0) for k in range(dias))

    cronica = suma(dias_cronico) / (dias_cronico / dias_agudo)
    if cronica == 0:
        return None
    return round(suma(dias_agudo) / cronica, 3)


Semaforo = Literal["baja", "verde", "amarillo", "rojo"]


def clasificar_acwr(
    acwr: float | None, *, min_seguro: float, max_seguro: float, alerta: float
) -> Semaforo | None:
    """< min: baja; min..max (ambos incluidos): verde; hasta `alerta` incluido:
    amarillo; por encima: rojo (REGLAS_NEGOCIO §18.3)."""
    if acwr is None:
        return None
    if acwr < min_seguro:
        return "baja"
    if acwr <= max_seguro:
        return "verde"
    if acwr <= alerta:
        return "amarillo"
    return "rojo"
