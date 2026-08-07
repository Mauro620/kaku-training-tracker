"""Persistencia de bloque. Una sesion tiene N bloques."""

import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bloque
from app.models.types import Distancia, Peso


async def crear(
    session: AsyncSession,
    *,
    sesion_id: uuid.UUID,
    ejercicio_id: int,
    orden: int,
    series: int | None,
    reps: int | None,
    distancia_m: Distancia | None,
    duracion_s: int | None,
    calidad: int | None,
    peso_kg: Peso | None,
    rpe: int | None,
    dolor_lumbar: bool,
) -> Bloque:
    """Inserta un bloque. No tiene idempotency_key: el cliente genera el
    `orden` por sesion, y la unicidad (sesion_id, orden) en la tabla evita
    duplicados. Si Fase 5 quiere reintentar, ese es el mecanismo."""
    bloque = Bloque(
        sesion_id=sesion_id,
        ejercicio_id=ejercicio_id,
        orden=orden,
        series=series,
        reps=reps,
        distancia_m=distancia_m,
        duracion_s=duracion_s,
        calidad=calidad,
        peso_kg=peso_kg,
        rpe=rpe,
        dolor_lumbar=dolor_lumbar,
    )
    session.add(bloque)
    await session.flush()
    return bloque


async def eliminar_por_sesion(session: AsyncSession, sesion_id: uuid.UUID) -> None:
    """Borra todos los bloques de la sesion, para reemplazarlos completos en
    un PUT (mismo patron que ciclo_semana_composicion.reemplazar: declarar
    todo de una vez evita bloques viejos colgando de un orden que ya no
    existe)."""
    await session.execute(delete(Bloque).where(Bloque.sesion_id == sesion_id))
