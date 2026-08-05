"""Endpoint de lectura de parámetros de negocio."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Parametro, Usuario
from app.schemas.catalogo.catalogo import ParametroRead
from app.services.catalogo import parametro as service

router = APIRouter(prefix="/parametros", tags=["parametros"])


@router.get(
    "/{clave}",
    response_model=ParametroRead,
    summary="Devuelve el valor vigente de un parámetro de negocio.",
)
async def leer_parametro(
    clave: str,
    _usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Parametro:
    return await service.obtener(sesion, clave)
