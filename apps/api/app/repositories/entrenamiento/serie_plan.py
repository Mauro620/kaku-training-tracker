"""Persistencia de serie_plan. Una sesion_plan tiene N series objetivo."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SeriePlan
from app.models.types import Peso


async def crear(
    session: AsyncSession,
    *,
    sesion_plan_id: int,
    ejercicio_id: int,
    orden: int,
    series: int,
    reps_min: int | None,
    reps_max: int | None,
    peso_objetivo_kg: Peso | None,
) -> SeriePlan:
    serie_plan = SeriePlan(
        sesion_plan_id=sesion_plan_id,
        ejercicio_id=ejercicio_id,
        orden=orden,
        series=series,
        reps_min=reps_min,
        reps_max=reps_max,
        peso_objetivo_kg=peso_objetivo_kg,
    )
    session.add(serie_plan)
    await session.flush()
    return serie_plan
