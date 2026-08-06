"""Endpoints de sesion y serie (Fase 4, ROADMAP §4).

POST /sesiones crea una sesion con sus series opcionales en el mismo body.
GET /sesiones?fecha=YYYY-MM-DD devuelve las sesiones del usuario en esa
fecha con sus series via selectinload.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    # Construimos los SerieCreate que el service espera, completando el
    # sesion_id despues de crear la sesion. El service reordena la logica
    # para que las series se inserten con el id real.
    sesion_creada, _ = await service.crear_sesion_con_series(
        sesion,
        usuario_id=usuario.id,
        sesion=payload,
        series_payload=series_payload,
    )
    await sesion.refresh(sesion_creada, attribute_names=["series"])
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
    resultado = await sesion.scalars(
        select(Sesion)
        .where(Sesion.usuario_id == usuario.id, Sesion.fecha == fecha)
        .options(selectinload(Sesion.series))
        .order_by(Sesion.registrado_en)
    )
    return list(resultado.all())
