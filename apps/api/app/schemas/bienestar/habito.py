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
