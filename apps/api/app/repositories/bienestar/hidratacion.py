"""Persistencia de registro_hidratacion. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistroHidratacion


async def sumar(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    fecha: date,
    cantidad_ml: int,
    idempotency_key: uuid.UUID | None,
) -> RegistroHidratacion:
    """Cada tap SUMA a `ml_totales`, no lo reemplaza.

    Fase 5: patron de 3 pasos igual al repo de Sueno/Habito. Con key:
    SELECT previo (idempotente) -> INSERT ON CONFLICT DO NOTHING -> si no
    creo nada, UPDATE que suma Y persiste la key nueva. Guardar la key en
    cada paso (no solo en el primer tap del dia) es lo que hace que un
    reintento de CUALQUIER tap, no solo el primero, sea idempotente.

    Nota de concurrencia: dos POSTs simultaneos con la misma key pueden
    pasar el SELECT previo y sumar dos veces. La cola de Fase 5 reintenta
    con delays (1s, 2s, ...), no concurrencia, asi que el riesgo es bajo.
    La forma atomica sin tabla de eventos exigiria cambiar el modelo
    (ver docs/PENDIENTES.md).
    """
    if idempotency_key is not None:
        existente = await session.scalar(
            select(RegistroHidratacion).where(
                RegistroHidratacion.idempotency_key == idempotency_key
            )
        )
        if existente is not None:
            return existente

        stmt = (
            pg_insert(RegistroHidratacion)
            .values(
                usuario_id=usuario_id,
                fecha=fecha,
                ml_totales=cantidad_ml,
                idempotency_key=idempotency_key,
            )
            .on_conflict_do_nothing()
            .returning(RegistroHidratacion)
        )
        creada = await session.scalar(stmt)
        if creada is not None:
            return creada

        actualizado = await session.scalar(
            update(RegistroHidratacion)
            .where(
                RegistroHidratacion.usuario_id == usuario_id,
                RegistroHidratacion.fecha == fecha,
            )
            .values(
                ml_totales=RegistroHidratacion.ml_totales + cantidad_ml,
                idempotency_key=idempotency_key,
            )
            .returning(RegistroHidratacion)
        )
        if actualizado is None:
            raise RuntimeError(
                "registro_hidratacion no encontrado despues de on_conflict_do_nothing"
            )
        return actualizado

    stmt = (
        pg_insert(RegistroHidratacion)
        .values(
            usuario_id=usuario_id,
            fecha=fecha,
            ml_totales=cantidad_ml,
            idempotency_key=idempotency_key,
        )
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
