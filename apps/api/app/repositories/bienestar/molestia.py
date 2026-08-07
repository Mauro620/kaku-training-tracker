"""Persistencia de molestia. Sin reglas de negocio.

Fase 5: ver patron de 3 pasos en el repo de Sueno.
"""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Molestia


async def upsert(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    fecha: date,
    zona_id: int,
    intensidad: int,
    nota: str | None,
    idempotency_key: uuid.UUID | None,
) -> Molestia:
    valores: dict[str, object] = {
        "usuario_id": usuario_id,
        "fecha": fecha,
        "zona_id": zona_id,
        "intensidad": intensidad,
        "nota": nota,
        "idempotency_key": idempotency_key,
    }

    if idempotency_key is not None:
        existente_por_key = await session.scalar(
            select(Molestia).where(Molestia.idempotency_key == idempotency_key)
        )
        if existente_por_key is not None:
            return existente_por_key

        stmt = (
            pg_insert(Molestia)
            .values(**valores)
            .on_conflict_do_nothing()
            .returning(Molestia)
        )
        creada = await session.scalar(stmt)
        if creada is not None:
            return creada

        actualizado = await session.scalar(
            update(Molestia)
            .where(
                Molestia.usuario_id == usuario_id,
                Molestia.fecha == fecha,
                Molestia.zona_id == zona_id,
            )
            .values(
                intensidad=intensidad,
                nota=nota,
                idempotency_key=idempotency_key,
            )
            .returning(Molestia)
        )
        if actualizado is None:
            raise RuntimeError(
                "molestia no encontrada despues de on_conflict_do_nothing"
            )
        return actualizado

    stmt = (
        pg_insert(Molestia)
        .values(**valores)
        .on_conflict_do_update(
            index_elements=["usuario_id", "fecha", "zona_id"],
            set_={"intensidad": intensidad, "nota": nota},
        )
        .returning(Molestia)
    )
    resultado = await session.scalar(stmt)
    return cast("Molestia", resultado)


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Molestia]:
    resultado = await session.scalars(
        select(Molestia)
        .where(Molestia.usuario_id == usuario_id, Molestia.fecha == fecha)
        .order_by(Molestia.zona_id)
    )
    return list(resultado.all())


async def obtener_por_id(session: AsyncSession, molestia_id: int) -> Molestia | None:
    return cast(
        "Molestia | None",
        await session.scalar(select(Molestia).where(Molestia.id == molestia_id)),
    )


async def eliminar(session: AsyncSession, molestia: Molestia) -> None:
    await session.delete(molestia)
    await session.flush()
