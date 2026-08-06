"""Orquestación de sesion_plan: crea validando el espaciado (REGLAS_NEGOCIO
§13.3) cuando el plan trae `dia_sugerido`."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import SesionPlan
from app.repositories import entrenamiento as repo
from app.schemas.entrenamiento.plan import SesionPlanCreate
from app.services.entrenamiento.ciclo import obtener_ciclo, obtener_semana
from app.services.entrenamiento.espaciado import validar_espaciado


async def crear_sesion_plan(
    session: AsyncSession, usuario_id: uuid.UUID, payload: SesionPlanCreate
) -> SesionPlan:
    ciclo = None
    if payload.ciclo_semana_id is not None:
        semana = await obtener_semana(session, usuario_id, payload.ciclo_semana_id)
        ciclo = await obtener_ciclo(session, usuario_id, semana.ciclo_id)

        tipos = {t.id: t for t in await repo.listar_tipos_sesion(session)}
        tipo_sesion = tipos.get(payload.tipo_sesion_id)
        if tipo_sesion is None:
            raise RecursoNoEncontradoError(
                f"tipo_sesion {payload.tipo_sesion_id} no encontrado"
            )

        await validar_espaciado(
            session,
            usuario_id=usuario_id,
            ciclo=ciclo,
            semana=semana,
            tipo_sesion=tipo_sesion,
            dia_sugerido=payload.dia_sugerido,
        )

    plan = await repo.crear_sesion_plan(
        session,
        usuario_id=usuario_id,
        ciclo_semana_id=payload.ciclo_semana_id,
        tipo_sesion_id=payload.tipo_sesion_id,
        fecha_prevista=payload.fecha_prevista,
        dia_sugerido=payload.dia_sugerido,
        objetivo=payload.objetivo,
        duracion_min_est=payload.duracion_min_est,
        rpe_objetivo=payload.rpe_objetivo,
    )
    await session.commit()
    await session.refresh(plan)
    return plan
