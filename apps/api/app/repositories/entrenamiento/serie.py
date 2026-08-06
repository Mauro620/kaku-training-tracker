"""Persistencia de serie. Una sesion tiene N series."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Serie


async def crear(
    session: AsyncSession,
    *,
    sesion_id: uuid.UUID,
    ejercicio_id: int,
    orden: int,
    series: int,
    reps: int,
    peso_kg: "object | None",
    rpe: int | None,
    dolor_lumbar: bool,
) -> Serie:
    """Inserta una serie. No tiene idempotency_key: el cliente genera el
    `orden` por sesion, y la unicidad (sesion_id, orden) en la tabla evita
    duplicados. Si Fase 5 quiere reintentar, ese es el mecanismo."""
    serie = Serie(
        sesion_id=sesion_id,
        ejercicio_id=ejercicio_id,
        orden=orden,
        series=series,
        reps=reps,
        peso_kg=peso_kg,
        rpe=rpe,
        dolor_lumbar=dolor_lumbar,
    )
    session.add(serie)
    await session.flush()
    return serie
