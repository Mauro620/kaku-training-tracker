"""Perfil del atleta: GET y PUT sobre el unico registro del usuario."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import PerfilAtleta, Usuario
from app.schemas.catalogo.perfil import PerfilRead, PerfilUpdate
from app.services.catalogo import perfil as service

router = APIRouter(prefix="/perfil", tags=["perfil"])


@router.get(
    "",
    response_model=PerfilRead,
    summary="Perfil del atleta. 404 si todavia no se creo.",
)
async def leer_perfil(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> PerfilAtleta:
    return await service.obtener_perfil(sesion, usuario.id)


@router.put(
    "",
    response_model=PerfilRead,
    summary="Crea o reemplaza el perfil completo del atleta.",
)
async def guardar_perfil(
    payload: PerfilUpdate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> PerfilAtleta:
    return await service.guardar_perfil(sesion, usuario.id, payload)
