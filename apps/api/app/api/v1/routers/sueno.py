"""Endpoints de registro_sueno. Validar, delegar al servicio, mapear a Read."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import RegistroSueno, Usuario
from app.schemas.bienestar.sueno import RegistroSuenoCreate, RegistroSuenoRead
from app.services.bienestar import sueno as service

router = APIRouter(prefix="/sueno", tags=["sueno"])


@router.post(
    "",
    response_model=RegistroSuenoRead,
    status_code=status.HTTP_200_OK,
    summary="Registra el sueño del día. Upsert por fecha.",
)
async def registrar_sueno(
    payload: RegistroSuenoCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroSueno:
    return await service.registrar(sesion, usuario.id, payload)


@router.get(
    "/ultimos",
    response_model=list[RegistroSuenoRead],
    summary="Devuelve los ultimos N dias de registros de sueño (incluyendo hoy).",
)
async def ultimos_n_dias(
    dias: int = Query(14, ge=1, le=60, description="Cantidad de dias hacia atras"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[RegistroSueno]:
    """Para H3 de la revision de UI: la pantalla Hoy pide 14 dias para
    la grilla/deuda. Limito a 60 para no tirar queries absurdas.

    La fecha "hoy" la calcula el server con la zona del proyecto, no
    la del cliente: el mismo registro de sueño corresponde a la misma
    fila para todos los usuarios en la misma zona."""
    zona = ZoneInfo(get_settings().tz)
    hoy_local = datetime.now(zona).date()
    return await service.listar_ultimos_n_dias(sesion, usuario.id, dias, hoy_local)


@router.get(
    "/{fecha}",
    response_model=RegistroSuenoRead,
    summary="Devuelve el registro de sueño de una fecha.",
)
async def leer_sueno(
    fecha: date,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> RegistroSueno:
    return await service.obtener(sesion, usuario.id, fecha)
