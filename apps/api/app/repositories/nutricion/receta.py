"""Persistencia de receta y receta_item. Sin reglas de negocio."""

import uuid
from decimal import Decimal
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Receta, RecetaItem
from app.models.enums import MomentoComida


async def crear(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    nombre: str,
    momento_default: MomentoComida | None,
) -> Receta:
    receta = Receta(
        usuario_id=usuario_id, nombre=nombre, momento_default=momento_default
    )
    session.add(receta)
    await session.flush()
    return receta


async def agregar_items(
    session: AsyncSession, receta_id: int, items: list[tuple[int, Decimal]]
) -> list[RecetaItem]:
    nuevos = [
        RecetaItem(receta_id=receta_id, alimento_id=alimento_id, cantidad_g=cantidad_g)
        for alimento_id, cantidad_g in items
    ]
    session.add_all(nuevos)
    await session.flush()
    return nuevos


async def eliminar_items(session: AsyncSession, receta_id: int) -> None:
    await session.execute(delete(RecetaItem).where(RecetaItem.receta_id == receta_id))


async def obtener_por_id(session: AsyncSession, receta_id: int) -> Receta | None:
    return cast(
        "Receta | None",
        await session.scalar(
            select(Receta)
            .where(Receta.id == receta_id)
            .options(selectinload(Receta.items))
        ),
    )


async def listar_por_usuario(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[Receta]:
    resultado = await session.scalars(
        select(Receta)
        .where(Receta.usuario_id == usuario_id, Receta.activa.is_(True))
        .options(selectinload(Receta.items))
        .order_by(Receta.nombre)
    )
    return list(resultado.all())


async def actualizar_cabecera(
    session: AsyncSession,
    receta: Receta,
    *,
    nombre: str,
    momento_default: MomentoComida | None,
) -> Receta:
    receta.nombre = nombre
    receta.momento_default = momento_default
    await session.flush()
    return receta


async def eliminar(session: AsyncSession, receta: Receta) -> None:
    await session.delete(receta)
    await session.flush()
