"""Schemas de Alimento (Fase 6, ROADMAP §6).

El catalogo de alimentos es un universo cerrado (~40 alimentos sembrados en
`app.seeds/alimentos.py`). El cliente solo lo lee: no hay Create/Update, un
alimento se agrega con una semilla + una migracion, no por endpoint.
"""

from decimal import Decimal

from app.models.enums import EstadoPesaje, GrupoAlimento
from app.schemas.base import ReadBase


class AlimentoRead(ReadBase):
    """`id` es integer (catalogo cerrado, ~40 filas). Si en algun momento
    cambia a uuid, hay que migrar el modelo y este schema."""

    id: int
    nombre: str
    grupo: GrupoAlimento
    estado_pesaje: EstadoPesaje
    kcal_100g: Decimal
    proteina_100g: Decimal
    carbo_100g: Decimal
    grasa_100g: Decimal
    fibra_100g: Decimal | None
    fuente: str | None
