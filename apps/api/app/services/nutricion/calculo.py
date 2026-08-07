"""Calculo de macros (REGLAS_NEGOCIO §12). Formula unica, no se repite
inline en receta.py ni comida.py."""

from dataclasses import dataclass
from decimal import Decimal

from app.models import Alimento


@dataclass(frozen=True)
class MacroTotal:
    kcal: Decimal
    proteina: Decimal
    carbo: Decimal
    grasa: Decimal
    fibra: Decimal


def calcular_macros(items: list[tuple[Alimento, Decimal]]) -> MacroTotal:
    """macro_total = Σ (macro_alimento_por_100g * cantidad_g / 100).

    `fibra_100g` es nullable en el catalogo (no todas las fuentes la
    reportan): un alimento sin ese dato aporta 0 a la fibra total en vez de
    invalidar el calculo completo."""
    kcal = Decimal("0")
    proteina = Decimal("0")
    carbo = Decimal("0")
    grasa = Decimal("0")
    fibra = Decimal("0")
    for alimento, cantidad_g in items:
        factor = cantidad_g / Decimal("100")
        kcal += alimento.kcal_100g * factor
        proteina += alimento.proteina_100g * factor
        carbo += alimento.carbo_100g * factor
        grasa += alimento.grasa_100g * factor
        if alimento.fibra_100g is not None:
            fibra += alimento.fibra_100g * factor
    return MacroTotal(
        kcal=kcal, proteina=proteina, carbo=carbo, grasa=grasa, fibra=fibra
    )


def sumar_macros(totales: list[MacroTotal]) -> MacroTotal:
    return MacroTotal(
        kcal=sum((t.kcal for t in totales), Decimal("0")),
        proteina=sum((t.proteina for t in totales), Decimal("0")),
        carbo=sum((t.carbo for t in totales), Decimal("0")),
        grasa=sum((t.grasa for t in totales), Decimal("0")),
        fibra=sum((t.fibra for t in totales), Decimal("0")),
    )
