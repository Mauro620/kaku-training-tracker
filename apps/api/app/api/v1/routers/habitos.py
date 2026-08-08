"""Endpoints de hábitos: catálogo del usuario + registro diario."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Habito, HabitoRegistro, Usuario
from app.schemas.bienestar.habito import (
    HabitoCreate,
    HabitoRead,
    HabitoRegistroCreate,
    HabitoRegistroRead,
    HabitoReordenar,
    HabitoUpdate,
)
from app.services.bienestar import habito as service

router = APIRouter(prefix="/habitos", tags=["habitos"])


@router.get(
    "/all",
    response_model=list[HabitoRead],
    summary="Lista TODOS los habitos del usuario (incluyendo archivados). Ajustes.",
)
async def listar_todos_habitos(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Habito]:
    return await service.listar_todos(sesion, usuario.id)


@router.post(
    "",
    response_model=HabitoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un habito del usuario.",
)
async def crear_habito(
    payload: HabitoCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Habito:
    return await service.crear_habito(
        sesion, usuario.id, nombre=payload.nombre, orden=payload.orden
    )


@router.patch(
    "/{habito_id}",
    response_model=HabitoRead,
    summary="Modifica nombre / orden / activo. activo=false ARCHIVA el habito.",
)
async def actualizar_habito(
    habito_id: int,
    payload: HabitoUpdate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Habito:
    return await service.actualizar_habito(
        sesion,
        usuario.id,
        habito_id,
        nombre=payload.nombre,
        activo=payload.activo,
        orden=payload.orden,
    )


@router.put(
    "/reordenar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reordena habitos aplicando el orden del array `ids`.",
)
async def reordenar_habitos(
    payload: HabitoReordenar,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    """El cliente envia la lista de ids en el orden que quiere. El
    server asigna `orden = indice` a cada uno. Items que no esten en
    la lista mantienen su posicion actual."""
    await service.reordenar_habitos(sesion, usuario.id, payload.ids)


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
