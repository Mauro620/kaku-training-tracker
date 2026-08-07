"""Persistencia de bloque_plan. Una sesion_plan tiene N bloques objetivo."""

from sqlalchemy import delete
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
    )
    session.add(bloque_plan)
    await session.flush()
    return bloque_plan


async def eliminar_por_sesion_plan(session: AsyncSession, sesion_plan_id: int) -> None:
    await session.execute(
        delete(BloquePlan).where(BloquePlan.sesion_plan_id == sesion_plan_id)
    )
