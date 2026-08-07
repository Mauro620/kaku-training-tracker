"""Persistencia de partido. Sin reglas de negocio.

`sesion_id` es unique: un partido ES una sesion (duracion y RPE viven ahi,
no se duplican). No hay idempotency_key propia: `sesion_id` unique ya
deduplica un reintento del mismo partido."""

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Partido, Sesion


async def crear(
    session: AsyncSession,
    *,
    sesion_id: uuid.UUID,
    rival: str | None,
    formato: str | None,
    minutos_jugados: int,
    goles: int,
    asistencias: int,
    recuperaciones: int | None,
    salio_bien: str | None,
    a_ajustar: str | None,
) -> Partido:
    """Idempotente por `sesion_id`: reintentar la creacion del mismo
    partido (misma sesion) devuelve la fila existente en vez de fallar por
    la unicidad."""
    stmt = (
        pg_insert(Partido)
        .values(
            sesion_id=sesion_id,
            rival=rival,
            formato=formato,
            minutos_jugados=minutos_jugados,
            goles=goles,
            asistencias=asistencias,
            recuperaciones=recuperaciones,
            salio_bien=salio_bien,
            a_ajustar=a_ajustar,
        )
        .on_conflict_do_nothing(index_elements=["sesion_id"])
        .returning(Partido)
    )
    creado = await session.scalar(stmt)
    if creado is not None:
        return creado

    existente = await session.scalar(
        select(Partido).where(Partido.sesion_id == sesion_id)
    )
    if existente is None:
        raise RuntimeError("partido no encontrado despues de on_conflict_do_nothing")
    return existente


async def obtener_por_id(
    session: AsyncSession, partido_id: uuid.UUID
) -> Partido | None:
    return await session.get(Partido, partido_id)


async def obtener_por_sesion(
    session: AsyncSession, sesion_id: uuid.UUID
) -> Partido | None:
    return cast(
        "Partido | None",
        await session.scalar(select(Partido).where(Partido.sesion_id == sesion_id)),
    )


async def listar_por_usuario(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[Partido]:
    resultado = await session.scalars(
        select(Partido)
        .join(Sesion, Sesion.id == Partido.sesion_id)
        .where(Sesion.usuario_id == usuario_id)
        .order_by(Sesion.fecha.desc())
    )
    return list(resultado.all())
