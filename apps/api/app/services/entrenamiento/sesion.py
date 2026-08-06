"""Orquestacion de sesion + series en una sola operacion.

El cliente (Fase 5 offline-first) puede reintentar el mismo POST con el
mismo `idempotency_key`: el repo de sesion es idempotente, pero las
series que se crearon la primera vez YA EXISTEN. Insertar otra vez
provocaria violacion de UNIQUE(sesion_id, orden).

Estrategia: comparamos la cantidad de series que la sesion ya tiene
contra la cantidad que el cliente envia. Si la sesion no tiene series,
es la primera vez (las creamos). Si ya tiene, es un retry (no hacemos
nada, devolvemos lo que hay).
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Serie, Sesion
from app.repositories import entrenamiento as repo
from app.schemas.entrenamiento.sesion import SerieSinSesionCreate, SesionCreate


async def crear_sesion_con_series(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    sesion: SesionCreate,
    series_payload: list[SerieSinSesionCreate],
) -> tuple[Sesion, int]:
    """Devuelve (sesion, series_creadas). Si series_creadas es 0, el
    `idempotency_key` ya existia: las series que devuelve son las que
    estaban."""
    sesion_creada = await repo.crear_sesion(
        session,
        sesion_id=sesion.id,
        idempotency_key=sesion.idempotency_key,
        usuario_id=usuario_id,
        sesion_plan_id=sesion.sesion_plan_id,
        fecha=sesion.fecha,
        tipo_sesion_id=sesion.tipo_sesion_id,
        duracion_min=sesion.duracion_min,
        rpe=sesion.rpe,
        nota=sesion.nota,
    )
    await session.flush()

    existentes = (
        await session.scalar(
            select(func.count())
            .select_from(Serie)
            .where(Serie.sesion_id == sesion_creada.id)
        )
        or 0
    )

    creadas = 0
    if existentes == 0 and series_payload:
        for sp in series_payload:
            await repo.crear_serie(
                session,
                sesion_id=sesion_creada.id,
                ejercicio_id=sp.ejercicio_id,
                orden=sp.orden,
                series=sp.series,
                reps=sp.reps,
                peso_kg=sp.peso_kg,
                rpe=sp.rpe,
                dolor_lumbar=sp.dolor_lumbar,
            )
            creadas += 1

    await session.commit()
    await session.refresh(sesion_creada)
    return sesion_creada, creadas


async def listar_sesiones_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Sesion]:
    return await repo.listar_sesiones_por_fecha(session, usuario_id, fecha)
