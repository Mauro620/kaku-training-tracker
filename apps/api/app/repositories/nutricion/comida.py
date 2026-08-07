"""Persistencia de comida_log y comida_item. Sin reglas de negocio."""

import uuid
from datetime import date
from decimal import Decimal
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ComidaItem, ComidaLog
from app.models.enums import MomentoComida


async def crear(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    idempotency_key: uuid.UUID,
    fecha: date,
    momento: MomentoComida,
    receta_id: int | None,
    nota: str | None,
) -> ComidaLog:
    """Inserta idempotente por `idempotency_key`. Si ya existe, devuelve la
    fila existente (mismo patron que sesion: multiples comidas por dia son
    normales, no hay unicidad natural que proteger salvo la key)."""
    stmt = (
        pg_insert(ComidaLog)
        .values(
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            fecha=fecha,
            momento=momento,
            receta_id=receta_id,
            nota=nota,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(ComidaLog)
    )
    creada = await session.scalar(stmt)
    if creada is not None:
        return creada

    existente = await session.scalar(
        select(ComidaLog).where(ComidaLog.idempotency_key == idempotency_key)
    )
    if existente is None:
        raise RuntimeError("comida_log no encontrada despues de on_conflict_do_nothing")
    return existente


async def agregar_items(
    session: AsyncSession, comida_log_id: uuid.UUID, items: list[tuple[int, Decimal]]
) -> list[ComidaItem]:
    nuevos = [
        ComidaItem(
            comida_log_id=comida_log_id, alimento_id=alimento_id, cantidad_g=cantidad_g
        )
        for alimento_id, cantidad_g in items
    ]
    session.add_all(nuevos)
    await session.flush()
    return nuevos


async def obtener_por_id(
    session: AsyncSession, comida_log_id: uuid.UUID
) -> ComidaLog | None:
    return cast(
        "ComidaLog | None",
        await session.scalar(
            select(ComidaLog)
            .where(ComidaLog.id == comida_log_id)
            .options(selectinload(ComidaLog.items))
        ),
    )


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[ComidaLog]:
    resultado = await session.scalars(
        select(ComidaLog)
        .where(ComidaLog.usuario_id == usuario_id, ComidaLog.fecha == fecha)
        .options(selectinload(ComidaLog.items))
        # MomentoComida se declara en orden cronologico (desayuno..cena) y
        # Postgres ordena un ENUM nativo por ese orden de declaracion, asi
        # que esto alcanza sin necesitar una columna de timestamp.
        .order_by(ComidaLog.momento, ComidaLog.id)
    )
    return list(resultado.all())


async def eliminar_items_de_comida(
    session: AsyncSession, comida_log_id: uuid.UUID
) -> None:
    """Usado por el servicio antes de borrar una comida_log: el FK no
    tiene ON DELETE CASCADE."""
    await session.execute(
        delete(ComidaItem).where(ComidaItem.comida_log_id == comida_log_id)
    )


async def eliminar(session: AsyncSession, comida: ComidaLog) -> None:
    await session.delete(comida)
    await session.flush()
