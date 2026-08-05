import uuid
from datetime import date

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import Intensidad


class MolestiaCreate(SchemaBase):
    """Sin molestia no hay fila: no existe un Create con intensidad 0."""

    fecha: date
    zona_id: int
    intensidad: Intensidad
    nota: str | None = None


class MolestiaUpdate(SchemaBase):
    intensidad: Intensidad | None = None
    nota: str | None = None


class MolestiaRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    fecha: date
    zona_id: int
    intensidad: int
    nota: str | None
