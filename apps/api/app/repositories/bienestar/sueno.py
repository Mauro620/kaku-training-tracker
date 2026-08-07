"""Persistencia de registro_sueno. Sin reglas de negocio (AGENTS.md/ARCHITECTURE.md).

Fase 5: el `idempotency_key` cubre la cola de sync. Politica: el cliente
genera una key POR INTENTO (no por documento). Repetir la misma key es
idempotente. Mandar key distinta con la misma fecha/zona es una edicion:
UPSERT por la unicidad natural (reemplaza datos y key).

El patron de 3 pasos es:
  1. INSERT con la key; si choca por key, SELECT por key (idempotente).
  2. Si la key NO existia pero `(usuario_id, fecha)` ya existia: UPDATE
     por la unicidad natural (edicion).
  3. Sin key: UPSERT directo por la unicidad natural (backfill Fase 9).
"""

import uuid
from datetime import date, datetime
from typing import cast

from sqlalchemy import select, update
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
    idempotency_key: uuid.UUID | None,
) -> RegistroSueno:
    valores: dict[str, object] = {
        "usuario_id": usuario_id,
        "fecha": fecha,
        "inicio": inicio,
        "fin": fin,
        "celular_fuera": celular_fuera,
        "origen": origen,
        "idempotency_key": idempotency_key,
    }

    if idempotency_key is not None:
        # Paso 1: SELECT previo por key. Si existe, idempotente.
        existente_por_key = await session.scalar(
            select(RegistroSueno).where(
                RegistroSueno.idempotency_key == idempotency_key
            )
        )
        if existente_por_key is not None:
            return existente_por_key

        # Paso 2: INSERT con la key. ON CONFLICT DO NOTHING sin target suprime
        # cualquier conflicto (key o unicidad natural), pero nosotros seguimos
        # para distinguir el caso "key ya estaba" del caso "fecha ya estaba".
        stmt = (
            pg_insert(RegistroSueno)
            .values(**valores)
            .on_conflict_do_nothing()
            .returning(RegistroSueno)
        )
        creada = await session.scalar(stmt)
        if creada is not None:
            return creada

        # Paso 3: el INSERT no creo nada. La key es nueva y la fecha ya
        # existia (edicion del cliente). UPDATE por la unicidad natural.
        actualizado = await session.scalar(
            update(RegistroSueno)
            .where(
                RegistroSueno.usuario_id == usuario_id,
                RegistroSueno.fecha == fecha,
            )
            .values(
                inicio=inicio,
                fin=fin,
                celular_fuera=celular_fuera,
                origen=origen,
                idempotency_key=idempotency_key,
            )
            .returning(RegistroSueno)
        )
        if actualizado is None:
            raise RuntimeError(
                "registro_sueno no encontrado despues de on_conflict_do_nothing"
            )
        return actualizado

    # Paso 3: sin key. UPSERT directo por (usuario_id, fecha).
    stmt = (
        pg_insert(RegistroSueno)
        .values(**valores)
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
