"""Persistencia de habito y habito_registro. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Habito, HabitoRegistro


async def listar_activos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Habito]:
    return list(
        (
            await session.scalars(
                select(Habito)
                .where(Habito.usuario_id == usuario_id, Habito.activo.is_(True))
                .order_by(Habito.orden)
            )
        ).all()
    )


async def obtener_habito(
    session: AsyncSession, usuario_id: uuid.UUID, habito_id: int
) -> Habito | None:
    return cast(
        "Habito | None",
        await session.scalar(
            select(Habito).where(
                Habito.id == habito_id, Habito.usuario_id == usuario_id
            )
        ),
    )


async def upsert_registro(
    session: AsyncSession, habito_id: int, fecha: date, valor: bool
) -> HabitoRegistro:
    """PK compuesta `(habito_id, fecha)`: es la deduplicación natural de la
    cola de sync (docs/schema.dbml)."""
    stmt = (
        pg_insert(HabitoRegistro)
        .values(habito_id=habito_id, fecha=fecha, valor=valor)
        .on_conflict_do_update(
            index_elements=["habito_id", "fecha"], set_={"valor": valor}
        )
        .returning(HabitoRegistro)
    )
    resultado = await session.scalar(stmt)
    return cast("HabitoRegistro", resultado)


async def listar_registros_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[HabitoRegistro]:
    return list(
        (
            await session.scalars(
                select(HabitoRegistro)
                .join(Habito, Habito.id == HabitoRegistro.habito_id)
                .where(Habito.usuario_id == usuario_id, HabitoRegistro.fecha == fecha)
            )
        ).all()
    )
