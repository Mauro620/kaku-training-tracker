import uuid
from datetime import date

from app.models.enums import OrigenDato
from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import Peso, Positivo


class MedidaCorporalCreate(SchemaBase):
    fecha: date
    peso_kg: Peso
    fc_reposo: Positivo | None = None


class MedidaCorporalRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    fecha: date
    peso_kg: Peso
    fc_reposo: int | None
    origen: OrigenDato
