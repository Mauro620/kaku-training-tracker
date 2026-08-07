"""Endpoints de Despensa (Fase 6, ROADMAP §6).

PUT reemplaza (imprescindible, en_stock) para un alimento del catalogo.
DELETE saca al alimento de la despensa del usuario.
La lista de mercado es: imprescindible = true AND en_stock = false.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Usuario
from app.repositories.nutricion.despensa import DespensaConAlimento
from app.schemas.nutricion.despensa import (
    DespensaListaDeMercadoRead,
    DespensaRead,
    DespensaUpsert,
)
from app.services.nutricion import despensa as service

router = APIRouter(prefix="/despensa", tags=["nutricion"])


def _a_read(item: DespensaConAlimento) -> DespensaRead:
    return DespensaRead(
        alimento_id=item.despensa.alimento_id,
        alimento_nombre=item.alimento.nombre,
        imprescindible=item.despensa.imprescindible,
        en_stock=item.despensa.en_stock,
    )


@router.get(
    "",
    response_model=list[DespensaRead],
    summary="Lista los alimentos que el usuario lleva a casa.",
)
async def listar_despensa(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[DespensaRead]:
    filas = await service.listar_despensa(sesion, usuario.id)
    return [_a_read(f) for f in filas]


@router.put(
    "/{alimento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reemplaza (imprescindible, en_stock) para un alimento.",
)
async def upsert_despensa(
    alimento_id: int,
    payload: DespensaUpsert,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    await service.upsert_despensa(
        sesion,
        usuario.id,
        alimento_id,
        imprescindible=payload.imprescindible,
        en_stock=payload.en_stock,
    )


@router.delete(
    "/{alimento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quita un alimento de la despensa del usuario.",
)
async def eliminar_de_despensa(
    alimento_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    await service.eliminar_de_despensa(sesion, usuario.id, alimento_id)


@router.get(
    "/lista-de-mercado",
    response_model=DespensaListaDeMercadoRead,
    summary="Items imprescindibles sin stock (lo que hay que comprar).",
)
async def lista_de_mercado(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> DespensaListaDeMercadoRead:
    filas = await service.lista_de_mercado(sesion, usuario.id)
    return DespensaListaDeMercadoRead(items=[_a_read(f) for f in filas])
