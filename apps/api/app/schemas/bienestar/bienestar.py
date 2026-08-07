import uuid
from datetime import date

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import ItemHooper


class RegistroBienestarCreate(SchemaBase):
    """Los cuatro ítems del Hooper. En los cuatro, 1 es bueno y 5 es malo.

    `idempotency_key` lo genera el cliente (Fase 5, offline-first). Nullable
    para admitir backfill historico (Fase 9, Notion).
    """

    fecha: date
    sueno_pobre: ItemHooper
    fatiga: ItemHooper
    dolor_muscular: ItemHooper
    estres: ItemHooper
    idempotency_key: uuid.UUID | None = None


class RegistroBienestarUpdate(SchemaBase):
    sueno_pobre: ItemHooper | None = None
    fatiga: ItemHooper | None = None
    dolor_muscular: ItemHooper | None = None
    estres: ItemHooper | None = None


class RegistroBienestarRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    fecha: date
    sueno_pobre: int
    fatiga: int
    dolor_muscular: int
    estres: int
    hooper: int
    idempotency_key: uuid.UUID | None
