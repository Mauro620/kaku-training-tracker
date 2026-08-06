"""Endpoints de sesion_plan (Fase 4 R2)."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import SesionPlan, Usuario
from app.schemas.entrenamiento.plan import SesionPlanCreate, SesionPlanRead
from app.services.entrenamiento.plan import crear_sesion_plan, listar_planes_de_fecha

router = APIRouter(prefix="/planes", tags=["ciclos"])


@router.post(
    "",
    response_model=SesionPlanRead,
    status_code=status.HTTP_200_OK,
    summary="Crea un plan de sesión. Valida espaciado si trae dia_sugerido.",
)
async def crear_plan(
    payload: SesionPlanCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> SesionPlan:
    return await crear_sesion_plan(sesion, usuario.id, payload)


@router.get(
    "",
    response_model=list[SesionPlanRead],
    summary="Planes de una fecha: fecha_prevista exacta o dia_sugerido resuelto.",
)
async def listar_planes(
    fecha: date = Query(..., description="Fecha local del registro"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[SesionPlan]:
    return await listar_planes_de_fecha(sesion, usuario.id, fecha)
