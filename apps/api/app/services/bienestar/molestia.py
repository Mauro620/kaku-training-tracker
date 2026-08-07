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

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Molestia
from app.repositories.bienestar import molestia as repo


async def registrar(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    fecha: date,
    zona_id: int,
    intensidad: int,
    nota: str | None,
    idempotency_key: uuid.UUID | None = None,
) -> Molestia:
    molestia = await repo.upsert(
        session,
        usuario_id=usuario_id,
        fecha=fecha,
        zona_id=zona_id,
        intensidad=intensidad,
        nota=nota,
        idempotency_key=idempotency_key,
    )
    await session.commit()
    await session.refresh(molestia)
    return molestia


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Molestia]:
    return await repo.listar_por_fecha(session, usuario_id, fecha)


async def eliminar(
    session: AsyncSession, usuario_id: uuid.UUID, molestia_id: int
) -> None:
    molestia = await repo.obtener_por_id(session, molestia_id)
    if molestia is None or molestia.usuario_id != usuario_id:
        raise RecursoNoEncontradoError(f"molestia {molestia_id} no encontrada")
    await repo.eliminar(session, molestia)
    await session.commit()
