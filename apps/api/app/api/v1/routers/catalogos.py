"""Endpoints de catalogos sembrados (Fase 1). El usuario no crea valores:
solo lee.

Estos endpoints existen para que el frontend pueda poblar los formularios
de seleccion (tipo de sesion en Entreno, ejercicio en una serie, zona
corporal en una molestia). Sin esto el front tendria que hardcodear los
valores, lo que rompe cuando el seed agrega uno nuevo.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Ejercicio, TipoSesion, Usuario, ZonaCorporal
from app.schemas.catalogo.catalogo import (
    EjercicioRead,
    TipoSesionRead,
    ZonaCorporalRead,
)
from app.services.catalogo import entrenamiento as service

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get(
    "/tipos-sesion",
    response_model=list[TipoSesionRead],
    summary="Lista los tipos de sesion sembrados.",
)
async def listar_tipos_sesion(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[TipoSesion]:
    return await service.listar_tipos_sesion(sesion)


@router.get(
    "/ejercicios",
    response_model=list[EjercicioRead],
    summary="Lista los ejercicios sembrados.",
)
async def listar_ejercicios(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Ejercicio]:
    return await service.listar_ejercicios(sesion)


@router.get(
    "/zonas-corporales",
    response_model=list[ZonaCorporalRead],
    summary="Lista las zonas corporales sembradas.",
)
async def listar_zonas_corporales(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[ZonaCorporal]:
    return await service.listar_zonas_corporales(sesion)
