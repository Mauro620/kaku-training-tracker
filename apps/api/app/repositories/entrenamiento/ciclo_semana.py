"""Persistencia de ciclo_semana. Sin reglas de negocio."""

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CicloSemana
from app.models.enums import FaseCiclo


async def crear(
    session: AsyncSession,
    *,
    ciclo_id: int,
    numero: int,
    fase: FaseCiclo,
    rpe_objetivo_min: int | None,
    rpe_objetivo_max: int | None,
    volumen_pct: int,
) -> CicloSemana:
    semana = CicloSemana(
        ciclo_id=ciclo_id,
        numero=numero,
        fase=fase,
        rpe_objetivo_min=rpe_objetivo_min,
        rpe_objetivo_max=rpe_objetivo_max,
        volumen_pct=volumen_pct,
    )
    session.add(semana)
    await session.flush()
    return semana


async def obtener_por_id(session: AsyncSession, semana_id: int) -> CicloSemana | None:
    return cast(
        "CicloSemana | None",
        await session.scalar(select(CicloSemana).where(CicloSemana.id == semana_id)),
    )


async def listar_por_ciclo(session: AsyncSession, ciclo_id: int) -> list[CicloSemana]:
    resultado = await session.scalars(
        select(CicloSemana)
        .where(CicloSemana.ciclo_id == ciclo_id)
        .order_by(CicloSemana.numero)
    )
    return list(resultado.all())
