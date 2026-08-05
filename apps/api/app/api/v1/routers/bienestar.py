"""Endpoints de registro_bienestar."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import RegistroBienestar, Usuario
from app.schemas.bienestar.bienestar import (
    RegistroBienestarCreate,
    RegistroBienestarRead,
)
from app.services.bienestar import bienestar as service

router = APIRouter(prefix="/bienestar", tags=["bienestar"])


@router.post(
    "",
    response_model=RegistroBienestarRead,
    status_code=status.HTTP_200_OK,
    summary="Registra el bienestar del día (índice de Hooper). Upsert por fecha.",
)
async def registrar_bienestar(
    payload: RegistroBienestarCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroBienestar:
    return await service.registrar(sesion, usuario.id, payload)


@router.get(
    "/{fecha}",
    response_model=RegistroBienestarRead,
    summary="Devuelve el registro de bienestar de una fecha.",
)
async def leer_bienestar(
    fecha: date,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroBienestar:
    return await service.obtener(sesion, usuario.id, fecha)
