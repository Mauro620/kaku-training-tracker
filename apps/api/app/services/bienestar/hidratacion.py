"""Reglas de negocio de registro_hidratacion. Sin invariante propia."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import RegistroHidratacion
from app.repositories.bienestar import hidratacion as repo


async def registrar(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date, cantidad_ml: int
) -> RegistroHidratacion:
    registro = await repo.sumar(session, usuario_id, fecha, cantidad_ml)
    await session.commit()
    return registro


async def obtener(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> RegistroHidratacion:
    registro = await repo.obtener_por_fecha(session, usuario_id, fecha)
    if registro is None:
        raise RecursoNoEncontradoError(f"sin registro de hidratación para {fecha}")
    return registro
