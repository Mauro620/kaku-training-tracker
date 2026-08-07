"""Rangos del dominio, en un solo lugar.

Los mismos rangos están como CHECK en la base. La validación de Pydantic
existe para devolver un 422 con un mensaje útil en vez de un 500 con un error
de integridad de Postgres; la base sigue siendo la que garantiza el invariante.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

Rpe = Annotated[int, Field(ge=1, le=10)]
"""RPE de 1 a 10 (REGLAS_NEGOCIO §1)."""

ItemHooper = Annotated[int, Field(ge=1, le=5)]
"""Ítem del índice de Hooper. 1 es bueno, 5 es malo (REGLAS_NEGOCIO §5)."""

Intensidad = Annotated[int, Field(ge=1, le=10)]
"""Intensidad de molestia. El 0 no existe: sin molestia no hay fila."""

DuracionMin = Annotated[int, Field(gt=0)]
Positivo = Annotated[int, Field(gt=0)]
NoNegativo = Annotated[int, Field(ge=0)]
Peso = Annotated[Decimal, Field(gt=0, max_digits=5, decimal_places=2)]

DiaSemana = Annotated[int, Field(ge=0, le=6)]
"""0=lunes..6=domingo (REGLAS_NEGOCIO §13.3)."""

Distancia = Annotated[Decimal, Field(gt=0, max_digits=5, decimal_places=1)]
DuracionSeg = Annotated[int, Field(gt=0)]
Calidad = Annotated[int, Field(ge=1, le=5)]
"""Calidad de ejecucion de un bloque tecnica. 1 malo, 5 excelente
(REGLAS_NEGOCIO §15)."""
