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


# Dos decimales: la precision de los macros que ve la UI. Si dejamos que
# el resultado salga con 4+ decimales (porque cantidad_g es Numeric(7,2)
# y la division por 100 amplifica la escala), la UI tendria que formatear
# en cada render. Mejor cerrar aca, una sola vez.
_PRECISION = Decimal("0.01")


def _q(valor: Decimal) -> Decimal:
    return valor.quantize(_PRECISION)


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
        kcal=_q(kcal),
        proteina=_q(proteina),
        carbo=_q(carbo),
        grasa=_q(grasa),
        fibra=_q(fibra),
    )


def sumar_macros(totales: list[MacroTotal]) -> MacroTotal:
    """Suma totales que ya vienen cuantizados de `calcular_macros`. La suma
    puede arrastrar un error de redondeo del ultimo digito: la cuantizamos
    una vez al final."""
    kcal = sum((t.kcal for t in totales), Decimal("0"))
    proteina = sum((t.proteina for t in totales), Decimal("0"))
    carbo = sum((t.carbo for t in totales), Decimal("0"))
    grasa = sum((t.grasa for t in totales), Decimal("0"))
    fibra = sum((t.fibra for t in totales), Decimal("0"))
    return MacroTotal(
        kcal=_q(kcal),
        proteina=_q(proteina),
        carbo=_q(carbo),
        grasa=_q(grasa),
        fibra=_q(fibra),
    )
