"""Endpoints de registro_hidratacion."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import RegistroHidratacion, Usuario
from app.schemas.bienestar.hidratacion import (
    RegistroHidratacionCreate,
    RegistroHidratacionRead,
)
from app.services.bienestar import hidratacion as service

router = APIRouter(prefix="/hidratacion", tags=["hidratacion"])


@router.post(
    "",
    response_model=RegistroHidratacionRead,
    status_code=status.HTTP_200_OK,
    summary="Suma una cantidad de agua al total del día.",
)
async def registrar_hidratacion(
    payload: RegistroHidratacionCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroHidratacion:
    return await service.registrar(
        sesion,
        usuario.id,
        payload.fecha,
        payload.cantidad_ml,
        idempotency_key=payload.idempotency_key,
    )


@router.get(
    "/{fecha}",
    response_model=RegistroHidratacionRead,
    summary="Devuelve el total de agua registrado en una fecha.",
)
async def leer_hidratacion(
    fecha: date,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroHidratacion:
    return await service.obtener(sesion, usuario.id, fecha)
