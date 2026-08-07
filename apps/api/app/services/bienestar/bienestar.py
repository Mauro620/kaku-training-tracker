"""Reglas de negocio de registro_bienestar.

Sin invariante propia: los rangos 1-5 ya los valida el schema de Pydantic y
el CHECK de la base. El servicio existe igual para que el router nunca
importe el repositorio directo (ARCHITECTURE.md §2)."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import RegistroBienestar
from app.repositories.bienestar import bienestar as repo
from app.schemas.bienestar.bienestar import RegistroBienestarCreate


async def registrar(
    session: AsyncSession, usuario_id: uuid.UUID, payload: RegistroBienestarCreate
) -> RegistroBienestar:
    registro = await repo.upsert_por_fecha(
        session,
        usuario_id=usuario_id,
        fecha=payload.fecha,
        sueno_pobre=payload.sueno_pobre,
        fatiga=payload.fatiga,
        dolor_muscular=payload.dolor_muscular,
        estres=payload.estres,
        idempotency_key=payload.idempotency_key,
    )
    await session.commit()
    return registro


async def obtener(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> RegistroBienestar:
    registro = await repo.obtener_por_fecha(session, usuario_id, fecha)
    if registro is None:
        raise RecursoNoEncontradoError(f"sin registro de bienestar para {fecha}")
    return registro
