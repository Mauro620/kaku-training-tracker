"""Endpoints de sesion y bloque (Fase 4, ROADMAP §4).

POST /sesiones crea una sesion con sus bloques opcionales en el mismo body.
GET /sesiones?fecha=YYYY-MM-DD devuelve las sesiones del usuario en esa
fecha con sus bloques via selectinload.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Sesion, Usuario
from app.schemas.entrenamiento.sesion import (
    BloqueSinSesionCreate,
    SesionCreate,
    SesionRead,
    SesionUpdate,
)
from app.services.entrenamiento import sesion as service

router = APIRouter(prefix="/sesiones", tags=["entrenamiento"])


@router.post(
    "",
    response_model=SesionRead,
    status_code=status.HTTP_200_OK,
    summary="Crea sesion con sus bloques (opcional). Idempotente por idempotency_key.",
)
async def crear_sesion(
    payload: SesionCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Sesion:
    bloques_payload: list[BloqueSinSesionCreate] = payload.bloques or []
    sesion_creada, _ = await service.crear_sesion_con_bloques(
        sesion,
        usuario_id=usuario.id,
        sesion=payload,
        bloques_payload=bloques_payload,
    )
    return sesion_creada


@router.get(
    "",
    response_model=list[SesionRead],
    summary="Sesiones del usuario en una fecha, con sus bloques.",
)
async def listar_sesiones(
    fecha: date = Query(..., description="Fecha local del registro"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Sesion]:
    return await service.listar_sesiones_de_fecha(sesion, usuario.id, fecha)


@router.get(
    "/{sesion_id}",
    response_model=SesionRead,
    summary="Detalle de una sesion, con sus bloques.",
)
async def obtener_sesion(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Sesion:
    return await service.obtener_sesion(sesion, usuario.id, sesion_id)


@router.put(
    "/{sesion_id}",
    response_model=SesionRead,
    summary="Reemplaza cabecera y bloques de la sesion (completo, no incremental).",
)
async def actualizar_sesion(
    sesion_id: uuid.UUID,
    payload: SesionUpdate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Sesion:
    return await service.actualizar_sesion(sesion, usuario.id, sesion_id, payload)


@router.delete(
    "/{sesion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina la sesion y sus bloques.",
)
async def eliminar_sesion(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    await service.eliminar_sesion(sesion, usuario.id, sesion_id)
