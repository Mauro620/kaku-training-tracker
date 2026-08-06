"""Persistencia de sesion_plan. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Ciclo, CicloSemana, SesionPlan


async def crear(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    ciclo_semana_id: int | None,
    tipo_sesion_id: int,
    fecha_prevista: date | None,
    dia_sugerido: int | None,
    objetivo: str | None,
    duracion_min_est: int | None,
    rpe_objetivo: int | None,
) -> SesionPlan:
    plan = SesionPlan(
        usuario_id=usuario_id,
        ciclo_semana_id=ciclo_semana_id,
        tipo_sesion_id=tipo_sesion_id,
        fecha_prevista=fecha_prevista,
        dia_sugerido=dia_sugerido,
        objetivo=objetivo,
        duracion_min_est=duracion_min_est,
        rpe_objetivo=rpe_objetivo,
    )
    session.add(plan)
    await session.flush()
    return plan


async def obtener_por_id(session: AsyncSession, plan_id: int) -> SesionPlan | None:
    return cast(
        "SesionPlan | None",
        await session.scalar(select(SesionPlan).where(SesionPlan.id == plan_id)),
    )


async def listar_por_ciclo_y_tipos(
    session: AsyncSession, ciclo_id: int, tipo_sesion_ids: list[int]
) -> list[SesionPlan]:
    """Planes del ciclo (cualquier semana) de alguno de los tipos dados, con
    `dia_sugerido` ya fijado. Usado para validar espaciado contra planes
    hermanos antes de que existan como sesion real."""
    if not tipo_sesion_ids:
        return []
    resultado = await session.scalars(
        select(SesionPlan)
        .join(CicloSemana, CicloSemana.id == SesionPlan.ciclo_semana_id)
        .where(
            CicloSemana.ciclo_id == ciclo_id,
            SesionPlan.tipo_sesion_id.in_(tipo_sesion_ids),
            SesionPlan.dia_sugerido.is_not(None),
        )
    )
    return list(resultado.all())


async def listar_candidatos_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[SesionPlan]:
    """Planes con `fecha_prevista` exacta, mas los que tienen `dia_sugerido`
    dentro del rango del ciclo al que pertenecen. El match exacto de dia
    (que requiere `ciclo_semana.numero`) lo resuelve el service: acá solo se
    acota por rango para no traer planes de otros ciclos."""
    resultado = await session.scalars(
        select(SesionPlan)
        .join(CicloSemana, CicloSemana.id == SesionPlan.ciclo_semana_id, isouter=True)
        .join(Ciclo, Ciclo.id == CicloSemana.ciclo_id, isouter=True)
        .where(
            SesionPlan.usuario_id == usuario_id,
            or_(
                SesionPlan.fecha_prevista == fecha,
                and_(
                    SesionPlan.dia_sugerido.is_not(None),
                    Ciclo.fecha_inicio <= fecha,
                    Ciclo.fecha_fin_prevista >= fecha,
                ),
            ),
        )
        .options(selectinload(SesionPlan.series_planeadas))
    )
    return list(resultado.all())
