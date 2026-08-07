"""Endpoints de molestia (Fase 4, ROADMAP §4).

Router aparte del de bienestar para evitar colision de paths: el router
de bienestar usa /{fecha} y /molestias matchearia con esa regla.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Molestia, Usuario
from app.schemas.bienestar.molestia import MolestiaCreate, MolestiaRead
from app.services.bienestar import molestia as service

router = APIRouter(prefix="/molestias", tags=["bienestar"])


@router.post(
    "",
    response_model=MolestiaRead,
    summary="Registra una molestia. Upsert por (fecha, zona).",
)
async def crear_molestia(
    payload: MolestiaCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Molestia:
    return await service.registrar(
        sesion,
        usuario.id,
        payload.fecha,
        payload.zona_id,
        payload.intensidad,
        payload.nota,
    )


@router.get(
    "",
    response_model=list[MolestiaRead],
    summary="Lista las molestias de una fecha.",
)
async def listar_molestias(
    fecha: date = Query(..., description="Fecha local del registro"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Molestia]:
    return await service.listar_por_fecha(sesion, usuario.id, fecha)


@router.delete(
    "/{molestia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina una molestia.",
)
async def eliminar_molestia(
    molestia_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    await service.eliminar(sesion, usuario.id, molestia_id)
