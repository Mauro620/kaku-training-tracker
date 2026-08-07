"""Schemas de Receta (Fase 6, ROADMAP §6, REGLAS_NEGOCIO §12).

PUT reemplaza la receta entera (cabecera + items): declarar todo de una vez
evita items viejos de un alimento que ya no forma parte de ella. Mismo
patron que Sesion y CicloSemanaComposicion.
"""

from decimal import Decimal

from pydantic import Field

from app.models.enums import MomentoComida
from app.schemas.base import ReadBase, SchemaBase


class RecetaItemCreate(SchemaBase):
    """`(alimento_id, cantidad_g)` que forman la receta.

    El backend valida que el alimento exista (servicio). `cantidad_g > 0` lo
    valida Pydantic aca para devolver 422 antes de tocar la base; el CHECK
    de Postgres es el cinturon de seguridad."""

    alimento_id: int
    cantidad_g: Decimal = Field(gt=0, max_digits=7, decimal_places=2)


class RecetaCreate(SchemaBase):
    nombre: str = Field(min_length=1, max_length=80)
    momento_default: MomentoComida | None = None
    items: list[RecetaItemCreate] = Field(min_length=1)


class RecetaUpdate(SchemaBase):
    """PUT reemplaza la receta entera."""

    nombre: str = Field(min_length=1, max_length=80)
    momento_default: MomentoComida | None = None
    items: list[RecetaItemCreate] = Field(min_length=1)


class RecetaItemRead(ReadBase):
    id: int
    alimento_id: int
    cantidad_g: Decimal


class RecetaRead(ReadBase):
    id: int
    nombre: str
    momento_default: MomentoComida | None
    activa: bool
    items: list[RecetaItemRead]


class MacroTotalRead(ReadBase):
    """Macros derivados (REGLAS_NEGOCIO §12). No se almacenan: se calculan
    al leer. Por eso viven como Read aca y no en el modelo."""

    kcal: Decimal
    proteina: Decimal
    carbo: Decimal
    grasa: Decimal
    fibra: Decimal
