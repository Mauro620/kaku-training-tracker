"""Reglas de negocio de despensa (Fase 6, ROADMAP §6).

La lista de mercado es: imprescindible = true AND en_stock = false.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.repositories import nutricion as repo
from app.repositories.nutricion.despensa import DespensaConAlimento


async def upsert_despensa(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    alimento_id: int,
    *,
    imprescindible: bool,
    en_stock: bool,
) -> None:
    """PUT reemplaza (imprescindible, en_stock) para un alimento.

    No se valida que el alimento exista en `alimento`: el FK en la DB lo
    rechaza, y el handler central lo traduce a 400/409. La UI solo
    muestra alimentos del catalogo asi que esto no pasa en la practica."""
    await repo.upsert_despensa(
        session,
        usuario_id,
        alimento_id,
        imprescindible=imprescindible,
        en_stock=en_stock,
    )
    await session.commit()


async def listar_despensa(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[DespensaConAlimento]:
    return await repo.listar_despensa_por_usuario(session, usuario_id)


async def lista_de_mercado(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[DespensaConAlimento]:
    return await repo.lista_de_mercado(session, usuario_id)


async def eliminar_de_despensa(
    session: AsyncSession, usuario_id: uuid.UUID, alimento_id: int
) -> None:
    """Quita un alimento de la despensa del usuario. Si no estaba, 404."""
    fila = await repo.obtener_despensa(session, usuario_id, alimento_id)
    if fila is None:
        raise RecursoNoEncontradoError(f"alimento {alimento_id} no esta en la despensa")
    await session.delete(fila)
    await session.commit()
