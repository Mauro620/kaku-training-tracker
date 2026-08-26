"""Persistencia de bloque. Una sesion tiene N bloques."""

import uuid

from sqlalchemy import delete, update
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
    nota: str | None = None,
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
        nota=nota,
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


async def reasignar_ejercicio(
    session: AsyncSession, *, origen_id: int, destino_id: int
) -> int:
    """UPDATE bloque SET ejercicio_id = destino WHERE ejercicio_id = origen.

    Usado por la fusion de ejercicios (R7): cuando se detecta que un
    ejercicio es duplicado de otro, los bloques historicos del origen se
    mueven al destino en una sola query, preservando la historia del
    usuario. Devuelve el rowcount (filas afectadas) para que el service
    pueda reportarlo en el cuerpo de la respuesta.
    """
    stmt = (
        update(Bloque)
        .where(Bloque.ejercicio_id == origen_id)
        .values(ejercicio_id=destino_id)
    )
    resultado = await session.execute(stmt)
    # `resultado.rowcount` existe en runtime (CursorResult), pero el tipo que
    # infiere mypy sobre `session.execute(update(...))` es `Result[Any]`, que
    # no lo expone. `getattr` con default 0 silencia a mypy y deja el
    # contrato explicito.
    return int(getattr(resultado, "rowcount", 0) or 0)
