"""Cálculo puro de las métricas de ciclo (REGLAS_NEGOCIO §17).

Sin acceso a la base: recibe listas y devuelve números, para que los casos de
REGLAS_NEGOCIO se prueben tal cual (AGENTS.md §3.5). El redondeo ocurre acá,
al serializar (§14): 1 decimal para porcentajes, horas y promedios.
"""

from collections.abc import Iterable, Sequence
from decimal import Decimal


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
