"""Persistencia de registro_sueno. Sin reglas de negocio (AGENTS.md/ARCHITECTURE.md)."""

import uuid
from datetime import date, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistroSueno
from app.models.enums import OrigenDato


async def upsert_por_fecha(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    fecha: date,
    inicio: datetime,
    fin: datetime,
    celular_fuera: bool | None,
    origen: OrigenDato,
) -> RegistroSueno:
    """Un registro por `(usuario_id, fecha)`: la unicidad de la tabla hace de
    deduplicación natural de la cola de sync (ARCHITECTURE.md §4.5)."""
    stmt = (
        pg_insert(RegistroSueno)
        .values(
            usuario_id=usuario_id,
            fecha=fecha,
            inicio=inicio,
            fin=fin,
            celular_fuera=celular_fuera,
            origen=origen,
        )
        .on_conflict_do_update(
            index_elements=["usuario_id", "fecha"],
            set_={
                "inicio": inicio,
                "fin": fin,
                "celular_fuera": celular_fuera,
                "origen": origen,
            },
        )
        .returning(RegistroSueno)
    )
    resultado = await session.scalar(stmt)
    return cast("RegistroSueno", resultado)


async def obtener_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> RegistroSueno | None:
    return cast(
        "RegistroSueno | None",
        await session.scalar(
            select(RegistroSueno).where(
                RegistroSueno.usuario_id == usuario_id, RegistroSueno.fecha == fecha
            )
        ),
    )
