"""Endpoints de Comida (Fase 6, ROADMAP §6, REGLAS_NEGOCIO §12).

Una comida tiene `receta_id` o items sueltos, no ambos. La validacion
xor se hace en el schema y en el servicio (el servicio tambien valida
que si no hay receta haya al menos un item).
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import ComidaLog, Usuario
from app.schemas.nutricion.comida import (
    ComidaConMacrosRead,
    ComidaCreate,
    ComidaRead,
    ComidasDelDiaRead,
)
from app.schemas.nutricion.receta import MacroTotalRead
from app.services.nutricion import comida as service
from app.services.nutricion.calculo import MacroTotal

router = APIRouter(prefix="/comidas", tags=["nutricion"])


@router.post(
    "",
    response_model=ComidaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una comida (con o sin receta).",
)
async def registrar_comida(
    payload: ComidaCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> ComidaLog:
    items = [(item.alimento_id, item.cantidad_g) for item in payload.items]
    return await service.registrar_comida(
        sesion,
        usuario.id,
        idempotency_key=payload.idempotency_key,
        fecha=payload.fecha,
        momento=payload.momento,
        receta_id=payload.receta_id,
        nota=payload.nota,
        items=items,
    )


@router.get(
    "",
    response_model=ComidasDelDiaRead,
    summary="Lista las comidas de un dia con macros agregados.",
)
async def listar_comidas_del_dia(
    fecha: date = Query(..., description="Fecha local del dia"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> ComidasDelDiaRead:
    comidas = await service.listar_comidas_del_dia(sesion, usuario.id, fecha)
    macros = await service.calcular_macros_del_dia(sesion, usuario.id, fecha)
    return ComidasDelDiaRead(
        comidas=[_comida_to_read(c) for c in comidas],
        macros_del_dia=_macros_to_read(macros),
    )


@router.get(
    "/{comida_id}",
    response_model=ComidaConMacrosRead,
    summary="Devuelve una comida con sus macros calculados.",
)
async def obtener_comida(
    comida_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> ComidaConMacrosRead:
    comida = await service.obtener_comida(sesion, usuario.id, comida_id)
    macros = await service.calcular_macros_de_comida(sesion, usuario.id, comida)
    base = _comida_to_read(comida)
    return ComidaConMacrosRead(**base.model_dump(), macros=_macros_to_read(macros))


@router.delete(
    "/{comida_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina una comida.",
)
async def eliminar_comida(
    comida_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    await service.eliminar_comida(sesion, usuario.id, comida_id)


def _comida_to_read(comida: ComidaLog) -> ComidaRead:
    return ComidaRead.model_validate(comida)


def _macros_to_read(total: MacroTotal) -> MacroTotalRead:
    return MacroTotalRead(
        kcal=total.kcal,
        proteina=total.proteina,
        carbo=total.carbo,
        grasa=total.grasa,
        fibra=total.fibra,
    )
