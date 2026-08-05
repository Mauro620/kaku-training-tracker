"""Persistencia de registro_hidratacion. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistroHidratacion


async def sumar(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date, cantidad_ml: int
) -> RegistroHidratacion:
    """Cada tap SUMA a `ml_totales`, no lo reemplaza."""
    stmt = (
        pg_insert(RegistroHidratacion)
        .values(usuario_id=usuario_id, fecha=fecha, ml_totales=cantidad_ml)
        .on_conflict_do_update(
            index_elements=["usuario_id", "fecha"],
            set_={
                "ml_totales": RegistroHidratacion.ml_totales + cantidad_ml,
            },
        )
        .returning(RegistroHidratacion)
    )
    resultado = await session.scalar(stmt)
    return cast("RegistroHidratacion", resultado)


async def obtener_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> RegistroHidratacion | None:
    return cast(
        "RegistroHidratacion | None",
        await session.scalar(
            select(RegistroHidratacion).where(
                RegistroHidratacion.usuario_id == usuario_id,
                RegistroHidratacion.fecha == fecha,
            )
        ),
    )
