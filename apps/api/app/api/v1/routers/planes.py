"""Endpoints de sesion_plan (Fase 4 R2)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import SesionPlan, Usuario
from app.schemas.entrenamiento.plan import SesionPlanCreate, SesionPlanRead
from app.services.entrenamiento.plan import crear_sesion_plan

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
