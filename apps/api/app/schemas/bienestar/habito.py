import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import NoNegativo


class HabitoCreate(SchemaBase):
    nombre: str = Field(min_length=1, max_length=60)
    activo: bool = True
    orden: NoNegativo = 0


class HabitoUpdate(SchemaBase):
    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    activo: bool | None = None
    orden: NoNegativo | None = None


class HabitoReordenar(SchemaBase):
    """El cliente manda la lista en el orden que quiere. El server
    actualiza el campo `orden` de cada habito segun la posicion en
    la lista. Items que no esten en la lista mantienen su orden
    anterior (no los borramos)."""

    ids: list[int] = Field(min_length=1)


class HabitoRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    nombre: str
    activo: bool
    orden: int


class HabitoRegistroCreate(SchemaBase):
    habito_id: int
    fecha: date
    valor: bool
    idempotency_key: uuid.UUID | None = None


class HabitoRegistroUpdate(SchemaBase):
    valor: bool


class HabitoRegistroRead(ReadBase):
    habito_id: int
    fecha: date
    valor: bool
    idempotency_key: uuid.UUID | None
