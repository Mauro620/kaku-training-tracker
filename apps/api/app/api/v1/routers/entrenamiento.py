"""Endpoints de sesion y serie (Fase 4, ROADMAP §4).

POST /sesiones crea una sesion con sus series opcionales en el mismo body.
GET /sesiones?fecha=YYYY-MM-DD devuelve las sesiones del usuario en esa
fecha con sus series via selectinload.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Sesion, Usuario
from app.schemas.entrenamiento.sesion import (
    SerieSinSesionCreate,
    SesionCreate,
    SesionRead,
)
from app.services.entrenamiento import sesion as service

router = APIRouter(prefix="/sesiones", tags=["entrenamiento"])


@router.post(
    "",
    response_model=SesionRead,
    status_code=status.HTTP_200_OK,
    summary="Crea sesion con sus series (opcional). Idempotente por idempotency_key.",
)
async def crear_sesion(
    payload: SesionCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Sesion:
    series_payload: list[SerieSinSesionCreate] = payload.series or []
    sesion_creada, _ = await service.crear_sesion_con_series(
        sesion,
        usuario_id=usuario.id,
        sesion=payload,
        series_payload=series_payload,
    )
    return sesion_creada


@router.get(
    "",
    response_model=list[SesionRead],
    summary="Sesiones del usuario en una fecha, con sus series.",
)
async def listar_sesiones(
    fecha: date = Query(..., description="Fecha local del registro"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Sesion]:
    return await service.listar_sesiones_de_fecha(sesion, usuario.id, fecha)
