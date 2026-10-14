"""Endpoints de sesion_plan (Fase 4 R2) y de importacion de plan semanal."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import SesionPlan, Usuario
from app.schemas.entrenamiento.importacion import (
    EXPORT_RECURSOS,
    ExportRead,
    ImportacionResultado,
    PlanSemanalImport,
)
from app.schemas.entrenamiento.plan import (
    PlanDetalleRead,
    SesionPlanCreate,
    SesionPlanRead,
)
from app.services.entrenamiento.importacion import (
    construir_export,
    importar_plan_semanal,
)
from app.services.entrenamiento.plan import (
    crear_sesion_plan,
    descartar_plan,
    listar_planes_de_fecha,
    obtener_plan_detalle,
    recuperar_plan,
)

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


@router.post(
    "/importar",
    response_model=ImportacionResultado,
    status_code=status.HTTP_200_OK,
    summary="Importa la planificación de una semana completa desde un JSON.",
    description=(
        "Crea o reemplaza los planes de una semana en una sola operación. Es "
        "idempotente por `{dia}-{tipo}`: reimportar la misma semana reemplaza "
        "en vez de duplicar. Los planes ya ejecutados (`cumplido` o `movido`) "
        "nunca se tocan; se omiten y se reportan como advertencia. El formato "
        "está en docs/features/feature-01-plan-import/PLAN_IMPORT.md."
    ),
)
async def importar_semana(
    payload: PlanSemanalImport,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> ImportacionResultado:
    return await importar_plan_semanal(sesion, usuario.id, payload)


@router.get(
    "/importar/export/{recurso}",
    response_model=ExportRead,
    summary="Exporta un recurso para armar el prompt del LLM (PLAN_IMPORT.md §9).",
    description=(
        "`recurso` es uno de `ejercicios`, `reglas`, `ejemplo`, `perfil` o "
        "`resumen_ciclo`. Cada uno devuelve un `contenido` listo para pegar. "
        "Un `recurso` desconocido responde 404, y `resumen_ciclo` tambien si "
        "no hay un ciclo activo ni cerrado."
    ),
)
async def exportar_recurso(
    recurso: str,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> ExportRead:
    if recurso not in EXPORT_RECURSOS:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return await construir_export(sesion, recurso, usuario.id)


@router.get(
    "/{plan_id}",
    response_model=PlanDetalleRead,
    summary="Detalle de un plan de sesión con sus bloques y ciclo.",
    description=(
        "Alimenta la pantalla previa a ejecutar (SPEC §3.8): el plan con su "
        "ciclo anidado y sus bloques planeados ordenados por `orden` ASC. 404 "
        "si el plan no existe o no es del usuario actual."
    ),
)
async def obtener_plan(
    plan_id: int = Path(..., description="id del sesion_plan"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> PlanDetalleRead:
    return await obtener_plan_detalle(sesion, usuario.id, plan_id)


@router.patch(
    "/{plan_id}/recuperar",
    response_model=SesionPlanRead,
    summary="Deshace un descarte: el plan descartado vuelve a pendiente.",
    description=(
        "Solo aplica a un plan `descartado`; con cualquier otro estado "
        "responde 422. `cumplido` y `movido` los resuelve el sistema contra "
        "la sesión real y no se tocan a mano."
    ),
)
async def recuperar(
    plan_id: int = Path(..., description="id del sesion_plan"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> SesionPlan:
    return await recuperar_plan(sesion, usuario.id, plan_id)


@router.patch(
    "/{plan_id}/descartar",
    response_model=SesionPlanRead,
    summary="El usuario declara que un plan no se va a hacer.",
    description=(
        "Única transición de estado que elige una persona: `cumplido` y "
        "`movido` los resuelve el sistema contra la sesión real. Un plan ya "
        "ejecutado no se puede descartar."
    ),
)
async def descartar(
    plan_id: int = Path(..., description="id del sesion_plan"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> SesionPlan:
    return await descartar_plan(sesion, usuario.id, plan_id)
