"""Endpoint 'cierre de semana' (C de la revision de UI).

Devuelve la data cruda por dia para que la UI renderice el grid 5x7
de cumplimiento. El backend NO calcula los flags: la regla de
cumplimiento (>= objetivo vs >= 80% del objetivo) es algo que va a
iterar y la iteracion es la UI.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import Usuario
from app.schemas.cierre_semana import CierreSemanaRead, DiaCierreSchema
from app.services.cierre_semana import DiaCierre, datos_crudos_por_dia

router = APIRouter(prefix="/semana", tags=["cierre-semana"])


@router.get(
    "",
    response_model=CierreSemanaRead,
    summary="Devuelve la data cruda por dia para el grid de cumplimiento semanal.",
)
async def cierre_semana(
    desde: date = Query(
        ..., description="Fecha local de inicio del rango (YYYY-MM-DD)"
    ),
    hasta: date = Query(..., description="Fecha local de fin del rango (YYYY-MM-DD)"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> CierreSemanaRead:
    """Rango inclusivo en ambos extremos. La UI envia tipicamente
    lunes..domingo (7 dias). El cap esta en 31 dias para no tirar queries
    absurdas; alcanza para un mes.
    """
    delta_dias = (hasta - desde).days + 1
    if delta_dias < 1 or delta_dias > 31:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="rango debe tener entre 1 y 31 dias",
        )

    dias = await datos_crudos_por_dia(sesion, usuario.id, desde, hasta)
    return CierreSemanaRead(
        dias=[_a_read(d) for d in dias],
    )


def _a_read(d: DiaCierre) -> DiaCierreSchema:
    return DiaCierreSchema(
        fecha=d.fecha,
        sueno={
            "horas": d.sueno_horas,
            "objetivo_h": d.sueno_objetivo_h,
        },
        sesion={"registrada": d.sesion_registrada},
        hidratacion={
            "ml_totales": d.hidratacion_ml_totales,
            "objetivo_ml": d.hidratacion_objetivo_ml,
        },
        habitos={
            "marcados": d.habitos_marcados,
            "activos": d.habitos_activos,
        },
        bienestar={"registrado": d.bienestar_registrado},
    )
