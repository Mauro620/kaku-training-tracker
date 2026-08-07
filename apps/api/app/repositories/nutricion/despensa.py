"""Persistencia de despensa. Sin reglas de negocio.

No es un espejo de todo el catalogo de `alimento`: solo existen filas para
los alimentos que el usuario agrego a su despensa. Un alimento nunca tocado
simplemente no aparece, no se asume "en stock" por default.
"""

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Despensa


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
) -> list[Despensa]:
    resultado = await session.scalars(
        select(Despensa).where(Despensa.usuario_id == usuario_id)
    )
    return list(resultado.all())


async def lista_de_mercado(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[Despensa]:
    resultado = await session.scalars(
        select(Despensa).where(
            Despensa.usuario_id == usuario_id,
            Despensa.imprescindible.is_(True),
            Despensa.en_stock.is_(False),
        )
    )
    return list(resultado.all())
