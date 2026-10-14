"""Exports `perfil` y `resumen_ciclo` para armar el prompt del LLM
(docs/features/feature-01-plan-import/PLAN_IMPORT.md §9).

Son JSON de solo lectura que el LLM usa como INSUMO para planear; no forman
parte del formato de importacion (version 2), que no cambia.
"""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import evaluacion as repo_evaluacion
from app.schemas.catalogo.perfil import PerfilRead
from app.services.catalogo import perfil as perfil_service
from app.services.metricas.resumen_ciclo import construir_resumen_ciclo


def _default(valor: Any) -> Any:
    # Decimal como numero y no como string: el consumidor es un LLM.
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    raise TypeError(f"no serializable: {type(valor)}")


def a_json(datos: Any) -> str:
    return json.dumps(datos, ensure_ascii=False, default=_default)


async def exportar_perfil(session: AsyncSession, usuario_id: uuid.UUID) -> str:
    perfil = PerfilRead.model_validate(
        await perfil_service.obtener_perfil(session, usuario_id)
    )
    medida = await repo_evaluacion.obtener_medida_mas_reciente(session, usuario_id)
    datos = perfil.model_dump(mode="python")
    # Dos pesos con significado distinto: `peso_kg` es el declarado en el
    # perfil; `ultima_medida` es el medido (medida_corporal).
    datos["ultima_medida"] = (
        {
            "fecha": medida.fecha,
            "peso_kg": medida.peso_kg,
            "cintura_cm": medida.cintura_cm,
        }
        if medida is not None
        else None
    )
    return a_json(datos)


async def exportar_resumen_ciclo(
    session: AsyncSession, usuario_id: uuid.UUID, hoy: date
) -> str:
    resumen = await construir_resumen_ciclo(session, usuario_id, hoy)
    return a_json(resumen.model_dump(mode="python"))
