"""Orquestación de sesion_plan: crea validando el espaciado (REGLAS_NEGOCIO
§13.3) cuando el plan trae `dia_sugerido`."""

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import CicloSemana, SesionPlan
from app.repositories import entrenamiento as repo
from app.schemas.entrenamiento.plan import SesionPlanCreate
from app.services.entrenamiento.ciclo import (
    calcular_rango_semana,
    obtener_ciclo,
    obtener_semana,
)
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
    for idx, sp in enumerate(payload.series or []):
        await repo.crear_serie_plan(
            session,
            sesion_plan_id=plan.id,
            ejercicio_id=sp.ejercicio_id,
            orden=idx + 1,
            series=sp.series,
            reps_min=sp.reps_min,
            reps_max=sp.reps_max,
            peso_objetivo_kg=sp.peso_objetivo_kg,
        )

    await session.commit()
    # attribute_names: SesionPlanRead siempre incluye series_planeadas, asi
    # que el service es quien las deja cargadas antes de devolver.
    await session.refresh(plan, attribute_names=["series_planeadas"])
    return plan


async def listar_planes_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[SesionPlan]:
    """Planes "de hoy" (ROADMAP §4): `fecha_prevista` exacta, o `dia_sugerido`
    que cae en `fecha` una vez resuelto contra el ciclo. El repo ya acota por
    rango del ciclo; acá se resuelve el dia exacto, que necesita
    `ciclo_semana.numero` y por eso no se puede hacer en una sola query."""
    candidatos = await repo.listar_planes_candidatos_de_fecha(
        session, usuario_id, fecha
    )
    semanas_cache: dict[int, CicloSemana | None] = {}
    resultado = []
    for plan in candidatos:
        if plan.fecha_prevista == fecha:
            resultado.append(plan)
            continue
        if plan.dia_sugerido is None or plan.ciclo_semana_id is None:
            continue
        if plan.ciclo_semana_id not in semanas_cache:
            semanas_cache[
                plan.ciclo_semana_id
            ] = await repo.obtener_ciclo_semana_por_id(session, plan.ciclo_semana_id)
        semana = semanas_cache[plan.ciclo_semana_id]
        if semana is None:
            continue
        ciclo = await obtener_ciclo(session, usuario_id, semana.ciclo_id)
        inicio_semana, _ = calcular_rango_semana(ciclo.fecha_inicio, semana.numero)
        if inicio_semana + timedelta(days=plan.dia_sugerido) == fecha:
            resultado.append(plan)
    return resultado
