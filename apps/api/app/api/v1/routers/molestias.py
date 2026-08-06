"""Endpoints de molestia (Fase 4, ROADMAP §4).

Router aparte del de bienestar para evitar colision de paths: el router
de bienestar usa /{fecha} y /molestias matchearia con esa regla.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Molestia, Usuario
from app.repositories.bienestar import molestia as repo
from app.schemas.bienestar.molestia import MolestiaCreate, MolestiaRead

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
    molestia = await repo.upsert(
        sesion,
        usuario_id=usuario.id,
        fecha=payload.fecha,
        zona_id=payload.zona_id,
        intensidad=payload.intensidad,
        nota=payload.nota,
    )
    await sesion.commit()
    await sesion.refresh(molestia)
    return molestia


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
    return await repo.listar_por_fecha(sesion, usuario.id, fecha)
