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
from app.repositories.catalogo import (
    ejercicio as repo_ejercicio,
)
from app.repositories.catalogo import (
    tipo_sesion as repo_tipo_sesion,
)
from app.repositories.catalogo import (
    zona_corporal as repo_zona_corporal,
)
from app.schemas.catalogo.catalogo import (
    EjercicioRead,
    TipoSesionRead,
    ZonaCorporalRead,
)

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
    return await repo_tipo_sesion.listar(sesion)


@router.get(
    "/ejercicios",
    response_model=list[EjercicioRead],
    summary="Lista los ejercicios sembrados.",
)
async def listar_ejercicios(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Ejercicio]:
    return await repo_ejercicio.listar(sesion)


@router.get(
    "/zonas-corporales",
    response_model=list[ZonaCorporalRead],
    summary="Lista las zonas corporales sembradas.",
)
async def listar_zonas_corporales(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[ZonaCorporal]:
    return await repo_zona_corporal.listar(sesion)
