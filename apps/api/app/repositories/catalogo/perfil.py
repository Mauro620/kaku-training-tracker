"""Persistencia de perfil_atleta. Sin reglas de negocio."""

import uuid
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PerfilAtleta


async def obtener(session: AsyncSession, usuario_id: uuid.UUID) -> PerfilAtleta | None:
    return cast(
        "PerfilAtleta | None",
        await session.scalar(
            select(PerfilAtleta).where(PerfilAtleta.usuario_id == usuario_id)
        ),
    )


async def upsert(
    session: AsyncSession, usuario_id: uuid.UUID, valores: dict[str, Any]
) -> PerfilAtleta:
    """INSERT ... ON CONFLICT DO UPDATE sobre la PK. `valores` trae todas las
    columnas editables: el PUT reemplaza el perfil entero."""
    stmt = (
        pg_insert(PerfilAtleta)
        .values(usuario_id=usuario_id, **valores)
        .on_conflict_do_update(
            index_elements=["usuario_id"],
            set_={**valores, "actualizado_en": func.now()},
        )
        .returning(PerfilAtleta)
    )
    # populate_existing: si el perfil ya estaba en la identity map, RETURNING
    # trae la fila nueva y hay que refrescar el objeto en vez de reusar el viejo.
    perfil = await session.scalar(stmt, execution_options={"populate_existing": True})
    assert perfil is not None  # RETURNING de un upsert siempre devuelve la fila
    return perfil
