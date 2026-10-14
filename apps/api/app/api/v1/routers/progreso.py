"""Las cuatro preguntas de la pestaña Progreso (REGLAS_NEGOCIO §18)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.core.tiempo import hoy_local
from app.db.session import get_session
from app.models import Usuario
from app.schemas.metricas.progreso import (
    ComposicionRead,
    CumplimientoRead,
    RecuperacionRead,
    RendimientoRead,
)
from app.services.metricas import progreso as service

router = APIRouter(prefix="/progreso", tags=["progreso"])

# Cuantas semanas de calendario mira una tarjeta de tendencia. Es de
# presentacion, no una regla de negocio: el cliente puede pedir otra ventana.
_SEMANAS_POR_DEFECTO = 8


@router.get(
    "/cumplimiento",
    response_model=CumplimientoRead,
    summary="¿Cumpliste el plan? % de sesiones por estado y semana del ciclo.",
)
async def cumplimiento(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> CumplimientoRead:
    return await service.cumplimiento(sesion, usuario.id, hoy_local())


@router.get(
    "/rendimiento",
    response_model=RendimientoRead,
    summary="¿Estás rindiendo mejor? Tendencia de pruebas y mejor marca por ejercicio.",
)
async def rendimiento(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RendimientoRead:
    return await service.rendimiento(sesion, usuario.id, hoy_local())


@router.get(
    "/recuperacion",
    response_model=RecuperacionRead,
    summary="¿Te estás recuperando? Carga semanal, ACWR con semáforo y sueño.",
)
async def recuperacion(
    semanas: int = Query(_SEMANAS_POR_DEFECTO, ge=1, le=26),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RecuperacionRead:
    return await service.recuperacion(sesion, usuario.id, hoy_local(), semanas)


@router.get(
    "/composicion",
    response_model=ComposicionRead,
    summary="¿Vas hacia tu objetivo de composición? Peso y cintura semanales.",
)
async def composicion(
    semanas: int = Query(_SEMANAS_POR_DEFECTO, ge=1, le=52),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> ComposicionRead:
    return await service.composicion(sesion, usuario.id, hoy_local(), semanas)
