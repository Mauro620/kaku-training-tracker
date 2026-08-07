"""Schemas de Comida (Fase 6, ROADMAP §6, REGLAS_NEGOCIO §12).

`receta_id` xor `items`: una comida con receta resuelve sus ingredientes
via `receta_item` y no lleva items sueltos; una sin receta exige al menos un
item (validacion de invariante en el servicio, no en el schema, porque
necesita leer la receta).
"""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field, model_validator

from app.models.enums import MomentoComida
from app.schemas.base import ReadBase, SchemaBase
from app.schemas.nutricion.receta import MacroTotalRead


class ComidaItemCreate(SchemaBase):
    alimento_id: int
    cantidad_g: Decimal = Field(gt=0, max_digits=7, decimal_places=2)


class ComidaCreate(SchemaBase):
    """`idempotency_key` lo genera el cliente (Fase 5, offline-first). Es
    la unica unicidad real: un usuario registra varias comidas en el mismo
    (fecha, momento), no hay PK natural que proteger.

    `receta_id` XOR `items`: ambos opcionales en el schema (no podemos
    leer receta en el schema), pero el validador temprano rechaza la
    combinacion invalida con 422 legible. La otra mitad (sin receta + sin
    items) la valida el servicio."""

    fecha: date
    momento: MomentoComida
    receta_id: int | None = None
    nota: str | None = None
    items: list[ComidaItemCreate] = Field(default_factory=list)
    idempotency_key: uuid.UUID

    @model_validator(mode="after")
    def _xor_receta_items(self) -> "ComidaCreate":
        if self.receta_id is not None and self.items:
            raise ValueError(
                "una comida con receta no lleva items sueltos: los "
                "ingredientes se resuelven via la receta"
            )
        return self


class ComidaItemRead(ReadBase):
    id: int
    alimento_id: int
    cantidad_g: Decimal


class ComidaRead(ReadBase):
    id: uuid.UUID
    fecha: date
    momento: MomentoComida
    receta_id: int | None
    nota: str | None
    idempotency_key: uuid.UUID
    items: list[ComidaItemRead]


class ComidaConMacrosRead(ComidaRead):
    """Comida + sus macros derivados. Usado por el endpoint
    /comidas/{id} (la UI muestra el detalle con macros)."""

    macros: MacroTotalRead


class ComidasDelDiaRead(SchemaBase):
    """Lista de comidas de un dia + macros agregados del dia.
    Un solo GET devuelve todo lo que la UI necesita."""

    comidas: list[ComidaRead]
    macros_del_dia: MacroTotalRead
