"""Persistencia de medida_corporal. Sin reglas de negocio.

Sin `idempotency_key`: la unicidad `(usuario_id, fecha)` ya es la
deduplicacion natural de la cola de sync (una medida semanal, no varios
intentos por dia como test_fisico)."""

import uuid
from datetime import date
from decimal import Decimal
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MedidaCorporal
from app.models.enums import OrigenDato


async def upsert(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    fecha: date,
    *,
    peso_kg: Decimal,
    fc_reposo: int | None,
    origen: OrigenDato,
) -> MedidaCorporal:
    stmt = (
        pg_insert(MedidaCorporal)
        .values(
            usuario_id=usuario_id,
            fecha=fecha,
            peso_kg=peso_kg,
            fc_reposo=fc_reposo,
            origen=origen,
        )
        .on_conflict_do_update(
            index_elements=["usuario_id", "fecha"],
            set_={"peso_kg": peso_kg, "fc_reposo": fc_reposo, "origen": origen},
        )
        .returning(MedidaCorporal)
    )
    resultado = await session.scalar(stmt)
    return cast("MedidaCorporal", resultado)


async def obtener_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> MedidaCorporal | None:
    return cast(
        "MedidaCorporal | None",
        await session.scalar(
            select(MedidaCorporal).where(
                MedidaCorporal.usuario_id == usuario_id, MedidaCorporal.fecha == fecha
            )
        ),
    )


async def obtener_mas_reciente(
    session: AsyncSession, usuario_id: uuid.UUID
) -> MedidaCorporal | None:
    return cast(
        "MedidaCorporal | None",
        await session.scalar(
            select(MedidaCorporal)
            .where(MedidaCorporal.usuario_id == usuario_id)
            .order_by(MedidaCorporal.fecha.desc())
            .limit(1)
        ),
    )


async def listar(session: AsyncSession, usuario_id: uuid.UUID) -> list[MedidaCorporal]:
    resultado = await session.scalars(
        select(MedidaCorporal)
        .where(MedidaCorporal.usuario_id == usuario_id)
        .order_by(MedidaCorporal.fecha.desc())
    )
    return list(resultado.all())
