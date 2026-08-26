"""Persistencia de bloque_plan. Una sesion_plan tiene N bloques objetivo."""

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BloquePlan
from app.models.types import Distancia, Peso


async def crear(
    session: AsyncSession,
    *,
    sesion_plan_id: int,
    ejercicio_id: int,
    orden: int,
    series: int | None,
    reps_min: int | None,
    reps_max: int | None,
    peso_objetivo_kg: Peso | None,
    distancia_objetivo_m: Distancia | None,
    duracion_objetivo_s: int | None,
    nota: str | None = None,
) -> BloquePlan:
    bloque_plan = BloquePlan(
        sesion_plan_id=sesion_plan_id,
        ejercicio_id=ejercicio_id,
        orden=orden,
        series=series,
        reps_min=reps_min,
        reps_max=reps_max,
        peso_objetivo_kg=peso_objetivo_kg,
        distancia_objetivo_m=distancia_objetivo_m,
        duracion_objetivo_s=duracion_objetivo_s,
        nota=nota,
    )
    session.add(bloque_plan)
    await session.flush()
    return bloque_plan


async def eliminar_por_sesion_plan(session: AsyncSession, sesion_plan_id: int) -> None:
    await session.execute(
        delete(BloquePlan).where(BloquePlan.sesion_plan_id == sesion_plan_id)
    )


async def reasignar_ejercicio(
    session: AsyncSession, *, origen_id: int, destino_id: int
) -> int:
    """UPDATE bloque_plan SET ejercicio_id = destino WHERE ejercicio_id = origen.

    Espejo de `bloque.reasignar_ejercicio` para la planificacion: cuando se
    fusionan dos ejercicios, los bloques objetivo del origen pasan al
    destino en una sola query. La historia del usuario se preserva.
    """
    stmt = (
        update(BloquePlan)
        .where(BloquePlan.ejercicio_id == origen_id)
        .values(ejercicio_id=destino_id)
    )
    resultado = await session.execute(stmt)
    # Ver bloque.reasignar_ejercicio: mismo motivo para getattr.
    return int(getattr(resultado, "rowcount", 0) or 0)
