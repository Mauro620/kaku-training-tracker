"""Endpoints de registro_sueno. Validar, delegar al servicio, mapear a Read."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import RegistroSueno, Usuario
from app.schemas.bienestar.sueno import RegistroSuenoCreate, RegistroSuenoRead
from app.services.bienestar import sueno as service

router = APIRouter(prefix="/sueno", tags=["sueno"])


@router.post(
    "",
    response_model=RegistroSuenoRead,
    status_code=status.HTTP_200_OK,
    summary="Registra el sueño del día. Upsert por fecha.",
)
async def registrar_sueno(
    payload: RegistroSuenoCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroSueno:
    return await service.registrar(sesion, usuario.id, payload)


@router.get(
    "/{fecha}",
    response_model=RegistroSuenoRead,
    summary="Devuelve el registro de sueño de una fecha.",
)
async def leer_sueno(
    fecha: date,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroSueno:
    return await service.obtener(sesion, usuario.id, fecha)
