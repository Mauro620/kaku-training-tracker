"""Calculo de test_fisico (REGLAS_NEGOCIO §7 y §8). Formulas unicas, no se
repiten inline en el service."""

from decimal import Decimal


def mejor_intento(valores: list[Decimal], mejor_es_mayor: bool) -> Decimal:
    return max(valores) if mejor_es_mayor else min(valores)


def calcular_pct_decremento(tiempos: list[Decimal]) -> Decimal | None:
    """Solo para tipo_test `rsa_30m` (REGLAS_NEGOCIO §7). Requiere al menos
    4 intentos; con menos, None.

    pct_decremento = 100 x (suma(tiempos) / (mejor x n)) - 100
    """
    n = len(tiempos)
    if n < 4:
        return None
    mejor = min(tiempos)
    pct = Decimal("100") * (sum(tiempos, Decimal("0")) / (mejor * n)) - Decimal("100")
    return pct.quantize(Decimal("0.001"))


def calcular_pct_cambio(
    valor_base: Decimal, valor_actual: Decimal, mejor_es_mayor: bool
) -> Decimal:
    """REGLAS_NEGOCIO §8. Positivo siempre significa mejora."""
    if mejor_es_mayor:
        pct = Decimal("100") * (valor_actual - valor_base) / valor_base
    else:
        pct = Decimal("100") * (valor_base - valor_actual) / valor_base
    return pct.quantize(Decimal("0.001"))
