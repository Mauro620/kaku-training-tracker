"""Persistencia de sesion. Sin reglas de negocio.

El `idempotency_key` es unique en la tabla (docs/schema.dbml): si el cliente
reintenta el mismo POST, el INSERT colisiona. Aqui manejamos la colision
con `on_conflict_do_nothing` + un SELECT posterior: si el key ya existia,
devolvemos la sesion que ya estaba. Asi Fase 5 puede reintentar sin miedo.
"""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Sesion


async def crear(
    session: AsyncSession,
    *,
    sesion_id: uuid.UUID | None,
    idempotency_key: uuid.UUID,
    usuario_id: uuid.UUID,
    sesion_plan_id: int | None,
    fecha: date,
    tipo_sesion_id: int,
    duracion_min: int,
    rpe: int,
    nota: str | None,
) -> Sesion:
    """Inserta idempotente por `idempotency_key`. Si ya existe, devuelve la
    fila existente. `carga_srpe` lo calcula Postgres (columna generada)."""
    valores: dict[str, object] = {
        "id": sesion_id,
        "idempotency_key": idempotency_key,
        "usuario_id": usuario_id,
        "sesion_plan_id": sesion_plan_id,
        "fecha": fecha,
        "tipo_sesion_id": tipo_sesion_id,
        "duracion_min": duracion_min,
        "rpe": rpe,
        "nota": nota,
    }
    stmt = (
        pg_insert(Sesion)
        .values(**valores)
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(Sesion)
    )
    creada = await session.scalar(stmt)
    if creada is not None:
        return creada

    # Ya existia: la devolvemos.
    existente = await session.scalar(
        select(Sesion).where(Sesion.idempotency_key == idempotency_key)
    )
    if existente is None:
        # No deberia pasar: o la creamos o existia.
        raise RuntimeError("sesion no encontrada despues de on_conflict_do_nothing")
    return existente


async def obtener_por_id(session: AsyncSession, sesion_id: uuid.UUID) -> Sesion | None:
    return cast(
        "Sesion | None",
        await session.scalar(select(Sesion).where(Sesion.id == sesion_id)),
    )


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Sesion]:
    resultado = await session.scalars(
        select(Sesion)
        .where(Sesion.usuario_id == usuario_id, Sesion.fecha == fecha)
        .order_by(Sesion.registrado_en)
    )
    return list(resultado.all())
