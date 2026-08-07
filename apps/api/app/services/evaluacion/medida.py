"""Servicio de medida_corporal. Passthrough: sin reglas de negocio propias
(el service existe igual para que el router nunca importe el repo directo,
ARCHITECTURE.md §2)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MedidaCorporal
from app.models.enums import OrigenDato
from app.repositories import evaluacion as repo


async def registrar_medida(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    fecha: date,
    peso_kg: Decimal,
    fc_reposo: int | None,
    origen: OrigenDato = OrigenDato.manual,
) -> MedidaCorporal:
    medida = await repo.upsert_medida(
        session, usuario_id, fecha, peso_kg=peso_kg, fc_reposo=fc_reposo, origen=origen
    )
    await session.commit()
    return medida


async def listar_medidas(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[MedidaCorporal]:
    return await repo.listar_medidas(session, usuario_id)
