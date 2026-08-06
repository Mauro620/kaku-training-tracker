"""Endpoints de ciclo, ciclo_semana, composición y cumplimiento (Fase 4 R2,
ROADMAP §4, REGLAS_NEGOCIO §13)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Ciclo, CicloSemana, CicloSemanaComposicion, Usuario
from app.schemas.entrenamiento.ciclo import (
    CicloCerrarRequest,
    CicloCreate,
    CicloRead,
    CicloSemanaCreate,
    CicloSemanaRead,
    ComposicionItemRead,
    CumplimientoItem,
    ReemplazarComposicionRequest,
)
from app.services.entrenamiento import ciclo as service

router = APIRouter(prefix="/ciclos", tags=["ciclos"])


@router.post("", response_model=CicloRead, summary="Crea un ciclo.")
async def crear_ciclo(
    payload: CicloCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Ciclo:
    return await service.crear_ciclo(sesion, usuario.id, payload)


@router.get("", response_model=list[CicloRead], summary="Lista los ciclos del usuario.")
async def listar_ciclos(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Ciclo]:
    return await service.listar_ciclos(sesion, usuario.id)


@router.get("/{ciclo_id}", response_model=CicloRead, summary="Devuelve un ciclo.")
async def obtener_ciclo(
    ciclo_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Ciclo:
    return await service.obtener_ciclo(sesion, usuario.id, ciclo_id)


@router.post(
    "/{ciclo_id}/cerrar",
    response_model=CicloRead,
    summary="Cierra el ciclo. fecha_cierre_real default hoy.",
)
async def cerrar_ciclo(
    ciclo_id: int,
    payload: CicloCerrarRequest = CicloCerrarRequest(),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Ciclo:
    return await service.cerrar_ciclo(
        sesion, usuario.id, ciclo_id, payload.fecha_cierre_real
    )


@router.post(
    "/{ciclo_id}/semanas",
    response_model=CicloSemanaRead,
    status_code=status.HTTP_200_OK,
    summary="Crea una semana dentro del ciclo.",
)
async def crear_semana(
    ciclo_id: int,
    payload: CicloSemanaCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> CicloSemana:
    return await service.crear_semana(
        sesion,
        usuario.id,
        ciclo_id,
        numero=payload.numero,
        fase=payload.fase,
        rpe_objetivo_min=payload.rpe_objetivo_min,
        rpe_objetivo_max=payload.rpe_objetivo_max,
        volumen_pct=payload.volumen_pct,
    )


@router.get(
    "/{ciclo_id}/semanas",
    response_model=list[CicloSemanaRead],
    summary="Lista las semanas del ciclo.",
)
async def listar_semanas(
    ciclo_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[CicloSemana]:
    return await service.listar_semanas(sesion, usuario.id, ciclo_id)


@router.put(
    "/semanas/{semana_id}/composicion",
    response_model=list[ComposicionItemRead],
    summary="Reemplaza la composición objetivo de la semana (completa, no incremental)",
)
async def reemplazar_composicion(
    semana_id: int,
    payload: ReemplazarComposicionRequest,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[CicloSemanaComposicion]:
    return await service.reemplazar_composicion(
        sesion, usuario.id, semana_id, payload.items
    )


@router.get(
    "/semanas/{semana_id}/cumplimiento",
    response_model=list[CumplimientoItem],
    summary="Cumplimiento de la semana: objetivo vs hecho por tipo de sesión.",
)
async def obtener_cumplimiento(
    semana_id: int,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[CumplimientoItem]:
    return await service.calcular_cumplimiento(sesion, usuario.id, semana_id)
