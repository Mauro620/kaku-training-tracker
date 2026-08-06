"""Persistencia de ciclo. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ciclo
from app.models.enums import EstadoCiclo


async def crear(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    numero: int,
    objetivo: str,
    fecha_inicio: date,
    semanas: int,
) -> Ciclo:
    ciclo = Ciclo(
        usuario_id=usuario_id,
        numero=numero,
        objetivo=objetivo,
        fecha_inicio=fecha_inicio,
        semanas=semanas,
    )
    session.add(ciclo)
    await session.flush()
    return ciclo


async def obtener_por_id(session: AsyncSession, ciclo_id: int) -> Ciclo | None:
    return cast(
        "Ciclo | None", await session.scalar(select(Ciclo).where(Ciclo.id == ciclo_id))
    )


async def listar_por_usuario(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[Ciclo]:
    resultado = await session.scalars(
        select(Ciclo)
        .where(Ciclo.usuario_id == usuario_id)
        .order_by(Ciclo.numero.desc())
    )
    return list(resultado.all())


async def cerrar(session: AsyncSession, ciclo: Ciclo, fecha_cierre_real: date) -> Ciclo:
    """Atómico con `estado=cerrado`: sin esto, el CHECK de la tabla
    (fecha_cierre_real IS NULL OR estado = cerrado) rechazaría un cierre
    con fecha pero sin el estado correspondiente."""
    ciclo.fecha_cierre_real = fecha_cierre_real
    ciclo.estado = EstadoCiclo.cerrado
    await session.flush()
    return ciclo
