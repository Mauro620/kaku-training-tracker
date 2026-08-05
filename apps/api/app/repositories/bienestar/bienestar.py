"""Persistencia de registro_bienestar. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistroBienestar


async def upsert_por_fecha(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    fecha: date,
    sueno_pobre: int,
    fatiga: int,
    dolor_muscular: int,
    estres: int,
) -> RegistroBienestar:
    stmt = (
        pg_insert(RegistroBienestar)
        .values(
            usuario_id=usuario_id,
            fecha=fecha,
            sueno_pobre=sueno_pobre,
            fatiga=fatiga,
            dolor_muscular=dolor_muscular,
            estres=estres,
        )
        .on_conflict_do_update(
            index_elements=["usuario_id", "fecha"],
            set_={
                "sueno_pobre": sueno_pobre,
                "fatiga": fatiga,
                "dolor_muscular": dolor_muscular,
                "estres": estres,
            },
        )
        .returning(RegistroBienestar)
    )
    resultado = await session.scalar(stmt)
    return cast("RegistroBienestar", resultado)


async def obtener_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> RegistroBienestar | None:
    return cast(
        "RegistroBienestar | None",
        await session.scalar(
            select(RegistroBienestar).where(
                RegistroBienestar.usuario_id == usuario_id,
                RegistroBienestar.fecha == fecha,
            )
        ),
    )
