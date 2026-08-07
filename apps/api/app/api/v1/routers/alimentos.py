"""Endpoints de Alimento (Fase 6, ROADMAP §6).

El catalogo de alimentos es un universo cerrado: el cliente solo lo lee,
no lo modifica. La creacion de un alimento nuevo es una decision de seed +
migracion, no un endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Alimento, Usuario
from app.schemas.nutricion.alimento import AlimentoRead
from app.services.nutricion import alimento as service

router = APIRouter(prefix="/alimentos", tags=["nutricion"])


@router.get(
    "",
    response_model=list[AlimentoRead],
    summary="Lista el catalogo de alimentos del sistema.",
)
async def listar_alimentos(
    _usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Alimento]:
    return await service.listar(sesion)
