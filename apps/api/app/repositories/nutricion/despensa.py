"""Persistencia de despensa. Sin reglas de negocio.

No es un espejo de todo el catalogo de `alimento`: solo existen filas para
los alimentos que el usuario agrego a su despensa. Un alimento nunca tocado
simplemente no aparece, no se asume "en stock" por default.
"""

import uuid
from dataclasses import dataclass
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alimento, Despensa


@dataclass(frozen=True)
class DespensaConAlimento:
    """`Despensa` + el nombre del alimento. El frontend lista por nombre y
    hacer el join en el repo evita N+1 cuando el usuario tiene varias filas."""

    despensa: Despensa
    alimento: Alimento


async def upsert(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    alimento_id: int,
    *,
    imprescindible: bool,
    en_stock: bool,
) -> Despensa:
    stmt = (
        pg_insert(Despensa)
        .values(
            usuario_id=usuario_id,
            alimento_id=alimento_id,
            imprescindible=imprescindible,
            en_stock=en_stock,
        )
        .on_conflict_do_update(
            index_elements=["usuario_id", "alimento_id"],
            set_={"imprescindible": imprescindible, "en_stock": en_stock},
        )
        .returning(Despensa)
    )
    resultado = await session.scalar(stmt)
    return cast("Despensa", resultado)


async def listar_por_usuario(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[DespensaConAlimento]:
    stmt = (
        select(Despensa, Alimento)
        .join(Alimento, Alimento.id == Despensa.alimento_id)
        .where(Despensa.usuario_id == usuario_id)
        .order_by(Alimento.nombre)
    )
    resultado = await session.execute(stmt)
    return [
        DespensaConAlimento(despensa=despensa, alimento=alimento)
        for despensa, alimento in resultado.all()
    ]


async def lista_de_mercado(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[DespensaConAlimento]:
    stmt = (
        select(Despensa, Alimento)
        .join(Alimento, Alimento.id == Despensa.alimento_id)
        .where(
            Despensa.usuario_id == usuario_id,
            Despensa.imprescindible.is_(True),
            Despensa.en_stock.is_(False),
        )
        .order_by(Alimento.nombre)
    )
    resultado = await session.execute(stmt)
    return [
        DespensaConAlimento(despensa=despensa, alimento=alimento)
        for despensa, alimento in resultado.all()
    ]


async def obtener(
    session: AsyncSession, usuario_id: uuid.UUID, alimento_id: int
) -> Despensa | None:
    """Para que el servicio valide pertenencia en el upsert (el PUT debe
    confirmar que existe si la fila ya estaba)."""
    return cast(
        "Despensa | None",
        await session.scalar(
            select(Despensa).where(
                Despensa.usuario_id == usuario_id,
                Despensa.alimento_id == alimento_id,
            )
        ),
    )
