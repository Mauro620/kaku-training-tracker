"""Endpoints de Receta (Fase 6, ROADMAP §6, REGLAS_NEGOCIO §12).

PUT reemplaza la receta completa (cabecera + items): declarar todo de una
vez evita items viejos de un alimento que ya no forma parte de ella.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Receta, Usuario
from app.schemas.nutricion.receta import (
    MacroTotalRead,
    RecetaCreate,
    RecetaRead,
    RecetaUpdate,
)
from app.services.nutricion import receta as service

router = APIRouter(prefix="/recetas", tags=["nutricion"])


@router.post(
    "",
    response_model=RecetaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una receta del usuario.",
)
async def crear_receta(
    payload: RecetaCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Receta:
    items = [(item.alimento_id, item.cantidad_g) for item in payload.items]
    return await service.crear_receta(
        sesion,
        usuario.id,
        nombre=payload.nombre,
        momento_default=payload.momento_default,
        items=items,
    )


@router.get(
    "",
    response_model=list[RecetaRead],
    summary="Lista las recetas activas del usuario.",
)
async def listar_recetas(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Receta]:
    return await service.listar_recetas(sesion, usuario.id)


@router.get(
    "/{receta_id}",
    response_model=RecetaRead,
    summary="Devuelve una receta del usuario.",
)
async def obtener_receta(
    receta_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Receta:
    return await service.obtener_receta(sesion, usuario.id, receta_id)


@router.put(
    "/{receta_id}",
    response_model=RecetaRead,
    summary="Reemplaza una receta completa (cabecera + items).",
)
async def actualizar_receta(
    receta_id: int,
    payload: RecetaUpdate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Receta:
    items = [(item.alimento_id, item.cantidad_g) for item in payload.items]
    return await service.actualizar_receta(
        sesion,
        usuario.id,
        receta_id,
        nombre=payload.nombre,
        momento_default=payload.momento_default,
        items=items,
    )


@router.delete(
    "/{receta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina una receta del usuario.",
)
async def eliminar_receta(
    receta_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    await service.eliminar_receta(sesion, usuario.id, receta_id)


@router.get(
    "/{receta_id}/macros",
    response_model=MacroTotalRead,
    summary="Calcula los macros de una receta (derivados, no almacenados).",
)
async def macros_de_receta(
    receta_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> MacroTotalRead:
    receta = await service.obtener_receta(sesion, usuario.id, receta_id)
    total = await service.calcular_macros_de_receta(sesion, receta)
    return MacroTotalRead(
        kcal=total.kcal,
        proteina=total.proteina,
        carbo=total.carbo,
        grasa=total.grasa,
        fibra=total.fibra,
    )
