"""Orquestación de sesion_plan: crea validando el espaciado (REGLAS_NEGOCIO
§13.3) cuando el plan trae `dia_sugerido`."""

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import CicloSemana, SesionPlan
from app.repositories import entrenamiento as repo
from app.schemas.entrenamiento.plan import SesionPlanCreate
from app.services.entrenamiento.bloque import validar_campos
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

    bloques_payload = payload.bloques or []
    ejercicios = {
        e.id: e
        for e in await repo.listar_ejercicios_por_ids(
            session, [b.ejercicio_id for b in bloques_payload]
        )
    }
    for b in bloques_payload:
        ejercicio = ejercicios.get(b.ejercicio_id)
        if ejercicio is None:
            raise RecursoNoEncontradoError(f"ejercicio {b.ejercicio_id} no encontrado")
        validar_campos(
            ejercicio.tipo_medicion,
            ejercicio_nombre=ejercicio.nombre,
            series=b.series,
            reps=b.reps_min if b.reps_min is not None else b.reps_max,
            peso=b.peso_objetivo_kg,
            distancia=b.distancia_objetivo_m,
            duracion=b.duracion_objetivo_s,
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
    for idx, b in enumerate(bloques_payload):
        await repo.crear_bloque_plan(
            session,
            sesion_plan_id=plan.id,
            ejercicio_id=b.ejercicio_id,
            orden=idx + 1,
            series=b.series,
            reps_min=b.reps_min,
            reps_max=b.reps_max,
            peso_objetivo_kg=b.peso_objetivo_kg,
            distancia_objetivo_m=b.distancia_objetivo_m,
            duracion_objetivo_s=b.duracion_objetivo_s,
        )

    await session.commit()
    # attribute_names: SesionPlanRead siempre incluye bloques_planeados, asi
    # que el service es quien los deja cargados antes de devolver.
    await session.refresh(plan, attribute_names=["bloques_planeados"])
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
