import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import model_validator

from app.models.enums import OrigenDato
from app.schemas.base import ReadBase, SchemaBase


class RegistroSuenoCreate(SchemaBase):
    """`usuario_id` no viaja en el cuerpo: sale del usuario autenticado.

    `idempotency_key` lo genera el cliente (Fase 5, offline-first). Si el
    cliente no lo manda, el backend igual lo acepta y le genera uno antes
    de la cola.
    """

    fecha: date
    inicio: datetime
    fin: datetime
    celular_fuera: bool | None = None
    origen: OrigenDato = OrigenDato.manual
    idempotency_key: uuid.UUID | None = None

    @model_validator(mode="after")
    def _fin_posterior_a_inicio(self) -> Self:
        if self.fin <= self.inicio:
            raise ValueError("fin tiene que ser posterior a inicio")
        return self


class RegistroSuenoUpdate(SchemaBase):
    inicio: datetime | None = None
    fin: datetime | None = None
    celular_fuera: bool | None = None
    origen: OrigenDato | None = None


class RegistroSuenoRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    fecha: date
    inicio: datetime
    fin: datetime
    celular_fuera: bool | None
    origen: OrigenDato
    horas_sueno: Decimal
    idempotency_key: uuid.UUID | None
