import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import ReadBase, SchemaBase


class RegistroHidratacionCreate(SchemaBase):
    """`cantidad_ml` es lo que se toma en ESTE tap (ej. un termo de 750ml),
    no el total del día: se suma a lo ya registrado.

    `idempotency_key` lo genera el cliente (Fase 5, offline-first). Cuando la
    cola reintenta con la misma key, el server no vuelve a sumar: idempotente
    contra el doble envio.
    """

    fecha: date
    cantidad_ml: int = Field(gt=0)
    idempotency_key: uuid.UUID | None = None


class RegistroHidratacionRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    fecha: date
    ml_totales: int
    idempotency_key: uuid.UUID | None
