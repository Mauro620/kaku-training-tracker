"""Persistencia de registro_bienestar. Sin reglas de negocio.

Fase 5: ver patron de 3 pasos en el repo de Sueno.
"""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select, update
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
    idempotency_key: uuid.UUID | None,
) -> RegistroBienestar:
    valores: dict[str, object] = {
        "usuario_id": usuario_id,
        "fecha": fecha,
        "sueno_pobre": sueno_pobre,
        "fatiga": fatiga,
        "dolor_muscular": dolor_muscular,
        "estres": estres,
        "idempotency_key": idempotency_key,
    }

    if idempotency_key is not None:
        existente_por_key = await session.scalar(
            select(RegistroBienestar).where(
                RegistroBienestar.idempotency_key == idempotency_key
            )
        )
        if existente_por_key is not None:
            return existente_por_key

        stmt = (
            pg_insert(RegistroBienestar)
            .values(**valores)
            .on_conflict_do_nothing()
            .returning(RegistroBienestar)
        )
        creada = await session.scalar(stmt)
        if creada is not None:
            return creada

        actualizado = await session.scalar(
            update(RegistroBienestar)
            .where(
                RegistroBienestar.usuario_id == usuario_id,
                RegistroBienestar.fecha == fecha,
            )
            .values(
                sueno_pobre=sueno_pobre,
                fatiga=fatiga,
                dolor_muscular=dolor_muscular,
                estres=estres,
                idempotency_key=idempotency_key,
            )
            .returning(RegistroBienestar)
        )
        if actualizado is None:
            raise RuntimeError(
                "registro_bienestar no encontrado despues de on_conflict_do_nothing"
            )
        return actualizado

    stmt = (
        pg_insert(RegistroBienestar)
        .values(**valores)
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
