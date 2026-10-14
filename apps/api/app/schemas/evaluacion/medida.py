import uuid
from datetime import date

from app.models.enums import OrigenDato
from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import Cintura, Peso, Positivo


class MedidaCorporalCreate(SchemaBase):
    fecha: date
    peso_kg: Peso
    fc_reposo: Positivo | None = None
    cintura_cm: Cintura | None = None


class MedidaCorporalRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    fecha: date
    peso_kg: Peso
    fc_reposo: int | None
    cintura_cm: Cintura | None
    origen: OrigenDato
