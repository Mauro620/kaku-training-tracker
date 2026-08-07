"""Tipos de columna reutilizables.

`Annotated` con un `mapped_column` adentro se puede compartir entre modelos sin
riesgo: SQLAlchemy construye una columna nueva en cada uso. Un `mapped_column`
suelto asignado a una variable de módulo, en cambio, se comparte y rompe el
mapeo del segundo modelo que lo use.
"""

import uuid
from decimal import Decimal
from typing import Annotated

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Uuid,
    text,
)
from sqlalchemy.orm import mapped_column

# ---------- Claves primarias ----------

SmallIntPk = Annotated[
    int, mapped_column(SmallInteger, primary_key=True, autoincrement=True)
]
IntPk = Annotated[int, mapped_column(Integer, primary_key=True, autoincrement=True)]
BigIntPk = Annotated[
    int, mapped_column(BigInteger, primary_key=True, autoincrement=True)
]

# El cliente genera el UUID antes de tener red (offline-first), así que casi
# siempre viene en el INSERT. El default del servidor es la red de contención
# para los inserts que nacen en el backend, como los seeds.
UuidPk = Annotated[
    uuid.UUID,
    mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
]

# ---------- Llaves foráneas ----------

UsuarioFk = Annotated[
    uuid.UUID, mapped_column(ForeignKey("usuario.id"), nullable=False)
]

# ---------- Sincronización ----------

# Hace la cola de salida segura ante reintentos: repetir la clave devuelve el
# recurso existente en vez de crear un duplicado. Nullable por defecto:
# la deduplicacion la hace la PK o unicidad natural de la tabla; el key
# es metadata para la cola de Fase 5, no una segunda unicidad. Nullable
# tambien para admitir backfill historico (Fase 9, Notion) sin UUID.
# Las entidades que requieren NOT NULL (Sesion, TestFisico) lo declaran
# explicitamente con un mapped_column nullable=False adicional.
IdempotencyKey = Annotated[uuid.UUID, mapped_column(Uuid, unique=True)]

# ---------- Numéricos del dominio ----------

Peso = Annotated[Decimal, mapped_column(Numeric(5, 2))]
Gramos = Annotated[Decimal, mapped_column(Numeric(7, 2))]
Macro = Annotated[Decimal, mapped_column(Numeric(5, 2))]
Distancia = Annotated[Decimal, mapped_column(Numeric(5, 1))]
