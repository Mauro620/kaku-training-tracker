"""Reglas de negocio de partido. Un partido ES una sesion: se crea sobre
una sesion existente, nunca suelto (REGLAS_NEGOCIO: duracion y RPE viven
en sesion, no se duplican aca)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Partido
from app.repositories import evaluacion as repo
from app.services.entrenamiento.sesion import obtener_sesion


async def registrar_partido(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    sesion_id: uuid.UUID,
    rival: str | None,
    formato: str | None,
    minutos_jugados: int,
    goles: int,
    asistencias: int,
    recuperaciones: int | None,
    salio_bien: str | None,
    a_ajustar: str | None,
) -> Partido:
    await obtener_sesion(session, usuario_id, sesion_id)  # valida dueño, 404 si no
    partido = await repo.crear_partido(
        session,
        sesion_id=sesion_id,
        rival=rival,
        formato=formato,
        minutos_jugados=minutos_jugados,
        goles=goles,
        asistencias=asistencias,
        recuperaciones=recuperaciones,
        salio_bien=salio_bien,
        a_ajustar=a_ajustar,
    )
    await session.commit()
    return partido


async def obtener_partido(
    session: AsyncSession, usuario_id: uuid.UUID, partido_id: uuid.UUID
) -> Partido:
    partido = await repo.obtener_partido_por_id(session, partido_id)
    if partido is None:
        raise RecursoNoEncontradoError(f"partido {partido_id} no encontrado")
    await obtener_sesion(session, usuario_id, partido.sesion_id)  # valida dueño
    return partido


async def listar_partidos(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[Partido]:
    return await repo.listar_partidos(session, usuario_id)
