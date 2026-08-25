"""Persistencia de sesion_plan. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Ciclo, CicloSemana, SesionPlan
from app.models.enums import EstadoSesionPlan


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
    clave_import: str | None = None,
    nombre: str | None = None,
    nota: str | None = None,
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
        clave_import=clave_import,
        nombre=nombre,
        nota=nota,
    )
    session.add(plan)
    await session.flush()
    return plan


async def actualizar_estado(
    session: AsyncSession, plan: SesionPlan, estado: EstadoSesionPlan
) -> SesionPlan:
    plan.estado = estado
    await session.flush()
    return plan


async def contar_ejecutados_de_ciclo(session: AsyncSession, ciclo_id: int) -> int:
    """Planes del ciclo (cualquier semana) que ya se ejecutaron. Es lo que
    decide si todavia se puede mover `ciclo.fecha_inicio`: una vez que hay
    algo hecho, correr la fecha cambiaria a que dia absoluto corresponde cada
    `dia_sugerido` y recalcularia mal el `cumplido`/`movido` del historico."""
    return (
        await session.scalar(
            select(func.count())
            .select_from(SesionPlan)
            .join(CicloSemana, CicloSemana.id == SesionPlan.ciclo_semana_id)
            .where(
                CicloSemana.ciclo_id == ciclo_id,
                SesionPlan.estado.in_(
                    [EstadoSesionPlan.cumplido, EstadoSesionPlan.movido]
                ),
            )
        )
    ) or 0


async def listar_por_semana_y_claves(
    session: AsyncSession, ciclo_semana_id: int, claves: list[str]
) -> list[SesionPlan]:
    """Planes importados de la semana cuya `clave_import` esta en la lista.
    Es lo que hace idempotente la reimportacion: el importador compara contra
    esto para decidir entre reemplazar, omitir o crear."""
    if not claves:
        return []
    resultado = await session.scalars(
        select(SesionPlan).where(
            SesionPlan.ciclo_semana_id == ciclo_semana_id,
            SesionPlan.clave_import.in_(claves),
        )
    )
    return list(resultado.all())


async def obtener_por_id(session: AsyncSession, plan_id: int) -> SesionPlan | None:
    return cast(
        "SesionPlan | None",
        await session.scalar(select(SesionPlan).where(SesionPlan.id == plan_id)),
    )


async def listar_por_ciclo_semana(
    session: AsyncSession, ciclo_semana_id: int
) -> list[SesionPlan]:
    resultado = await session.scalars(
        select(SesionPlan)
        .where(SesionPlan.ciclo_semana_id == ciclo_semana_id)
        .options(selectinload(SesionPlan.bloques_planeados))
    )
    return list(resultado.all())


async def eliminar(session: AsyncSession, plan: SesionPlan) -> None:
    await session.delete(plan)
    await session.flush()


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
        .options(selectinload(SesionPlan.bloques_planeados))
    )
    return list(resultado.all())
