"""Lógica de negocio de molestia.

Passthrough: la unicidad (usuario_id, fecha, zona_id) la cubre el repo con
ON CONFLICT. Si Fase 8 quiere reglas (ej. "una molestia lumbar hoy dispara
señal de descarga"), este es el lugar. El service existe igual sin
invariante propia: ARCHITECTURE.md §2 exige que el router nunca importe el
repositorio directo, ni siquiera cuando no hay lógica que orquestar.
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Molestia
from app.repositories.bienestar import molestia as repo


async def registrar(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    fecha: date,
    zona_id: int,
    intensidad: int,
    nota: str | None,
) -> Molestia:
    molestia = await repo.upsert(
        session,
        usuario_id=usuario_id,
        fecha=fecha,
        zona_id=zona_id,
        intensidad=intensidad,
        nota=nota,
    )
    await session.commit()
    await session.refresh(molestia)
    return molestia


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Molestia]:
    return await repo.listar_por_fecha(session, usuario_id, fecha)
