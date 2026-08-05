"""Endpoints de hábitos: catálogo del usuario + registro diario."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Habito, HabitoRegistro, Usuario
from app.schemas.bienestar.habito import (
    HabitoRead,
    HabitoRegistroCreate,
    HabitoRegistroRead,
)
from app.services.bienestar import habito as service

router = APIRouter(prefix="/habitos", tags=["habitos"])


@router.get(
    "",
    response_model=list[HabitoRead],
    summary="Lista los hábitos activos del usuario.",
)
async def listar_habitos(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Habito]:
    return await service.listar_habitos(sesion, usuario.id)


@router.get(
    "/registro/{fecha}",
    response_model=list[HabitoRegistroRead],
    summary="Lista los hábitos ya registrados en una fecha.",
)
async def leer_registros(
    fecha: date,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[HabitoRegistro]:
    return await service.listar_registros_de_fecha(sesion, usuario.id, fecha)


@router.post(
    "/registro",
    response_model=HabitoRegistroRead,
    status_code=status.HTTP_200_OK,
    summary="Marca un hábito para una fecha. Upsert por (habito_id, fecha).",
)
async def registrar_habito(
    payload: HabitoRegistroCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> HabitoRegistro:
    return await service.registrar(sesion, usuario.id, payload)
