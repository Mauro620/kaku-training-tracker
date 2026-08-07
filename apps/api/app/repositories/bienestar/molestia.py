"""Persistencia de molestia. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Molestia


async def upsert(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    fecha: date,
    zona_id: int,
    intensidad: int,
    nota: str | None,
) -> Molestia:
    """Unicidad (usuario_id, fecha, zona_id) en la tabla: si el usuario
    marca dos veces la misma zona el mismo dia, se actualiza la intensidad."""
    stmt = (
        pg_insert(Molestia)
        .values(
            usuario_id=usuario_id,
            fecha=fecha,
            zona_id=zona_id,
            intensidad=intensidad,
            nota=nota,
        )
        .on_conflict_do_update(
            index_elements=["usuario_id", "fecha", "zona_id"],
            set_={"intensidad": intensidad, "nota": nota},
        )
        .returning(Molestia)
    )
    resultado = await session.scalar(stmt)
    return cast("Molestia", resultado)


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Molestia]:
    resultado = await session.scalars(
        select(Molestia)
        .where(Molestia.usuario_id == usuario_id, Molestia.fecha == fecha)
        .order_by(Molestia.zona_id)
    )
    return list(resultado.all())


async def obtener_por_id(session: AsyncSession, molestia_id: int) -> Molestia | None:
    return cast(
        "Molestia | None",
        await session.scalar(select(Molestia).where(Molestia.id == molestia_id)),
    )


async def eliminar(session: AsyncSession, molestia: Molestia) -> None:
    await session.delete(molestia)
    await session.flush()
