"""Reglas de negocio de registro_sueno. Sin HTTP ni SQL (AGENTS.md/ARCHITECTURE.md)."""

import uuid
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import InvarianteDeNegocioError, RecursoNoEncontradoError
from app.models import RegistroSueno
from app.repositories.bienestar import sueno as repo
from app.schemas.bienestar.sueno import RegistroSuenoCreate


def _validar_fecha_del_despertar(payload: RegistroSuenoCreate) -> None:
    """`fecha` es la fecha del despertar: tiene que ser la fecha local de
    `fin` (docs/schema.dbml, docs/PENDIENTES.md). No se puede exigir con un
    CHECK ni con una columna generada porque la conversión de zona horaria no
    es IMMUTABLE en Postgres; el servicio es quien lo garantiza."""
    zona = ZoneInfo(get_settings().tz)
    fecha_local_de_fin = payload.fin.astimezone(zona).date()
    if payload.fecha != fecha_local_de_fin:
        raise InvarianteDeNegocioError(
            f"fecha ({payload.fecha}) no coincide con la fecha local de fin "
            f"({fecha_local_de_fin})"
        )


async def registrar(
    session: AsyncSession, usuario_id: uuid.UUID, payload: RegistroSuenoCreate
) -> RegistroSueno:
    _validar_fecha_del_despertar(payload)
    registro = await repo.upsert_por_fecha(
        session,
        usuario_id=usuario_id,
        fecha=payload.fecha,
        inicio=payload.inicio,
        fin=payload.fin,
        celular_fuera=payload.celular_fuera,
        origen=payload.origen,
    )
    await session.commit()
    return registro


async def obtener(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> RegistroSueno:
    registro = await repo.obtener_por_fecha(session, usuario_id, fecha)
    if registro is None:
        raise RecursoNoEncontradoError(f"sin registro de sueño para {fecha}")
    return registro
