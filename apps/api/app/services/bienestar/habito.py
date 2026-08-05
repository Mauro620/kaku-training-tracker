"""Reglas de negocio de habito y habito_registro."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Habito, HabitoRegistro
from app.repositories.bienestar import habito as repo
from app.schemas.bienestar.habito import HabitoRegistroCreate


async def listar_habitos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Habito]:
    return await repo.listar_activos(session, usuario_id)


async def registrar(
    session: AsyncSession, usuario_id: uuid.UUID, payload: HabitoRegistroCreate
) -> HabitoRegistro:
    # El hábito tiene que existir Y pertenecer al usuario: sin este chequeo,
    # cualquiera podría marcar el hábito de otro usuario por id.
    habito = await repo.obtener_habito(session, usuario_id, payload.habito_id)
    if habito is None:
        raise RecursoNoEncontradoError(f"hábito {payload.habito_id} no encontrado")

    registro = await repo.upsert_registro(
        session, payload.habito_id, payload.fecha, payload.valor
    )
    await session.commit()
    return registro


async def listar_registros_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[HabitoRegistro]:
    return await repo.listar_registros_por_fecha(session, usuario_id, fecha)
