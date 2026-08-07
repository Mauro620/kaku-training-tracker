import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import ValorTest


class TestFisicoCreate(SchemaBase):
    """`idempotency_key` la genera el cliente: `(usuario_id, tipo_test_id,
    fecha)` no es unico a proposito (se puede repetir un test el mismo
    dia), asi que la key es la unica proteccion contra reintentos
    duplicados de la cola."""

    idempotency_key: uuid.UUID
    fecha: date
    tipo_test_id: int
    superficie: str | None = Field(default=None, max_length=40)
    condiciones: str | None = None
    valores: list[ValorTest] = Field(min_length=1)


class TestIntentoRead(ReadBase):
    numero: int
    valor: ValorTest


class TestFisicoRead(ReadBase):
    id: uuid.UUID
    usuario_id: uuid.UUID
    fecha: date
    tipo_test_id: int
    superficie: str | None
    condiciones: str | None
    intentos: list[TestIntentoRead] = Field(default_factory=list)


class ResultadoTestRead(SchemaBase):
    mejor: ValorTest
    media: ValorTest
    # Porcentajes, no mediciones crudas: pueden ser negativos (un pct_cambio
    # negativo es un retroceso real) asi que no reusan ValorTest (gt=0).
    pct_decremento: Decimal | None
    pct_cambio: Decimal | None
