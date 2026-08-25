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


async def obtener_por_numero(
    session: AsyncSession, usuario_id: uuid.UUID, numero: int
) -> Ciclo | None:
    """UNIQUE(usuario_id, numero): el numero de ciclo es su identidad para el
    usuario, y es lo unico que trae el JSON de importacion."""
    return cast(
        "Ciclo | None",
        await session.scalar(
            select(Ciclo).where(Ciclo.usuario_id == usuario_id, Ciclo.numero == numero)
        ),
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


async def actualizar(
    session: AsyncSession,
    ciclo: Ciclo,
    *,
    objetivo: str,
    fecha_inicio: date,
    semanas: int,
) -> Ciclo:
    """`numero` no se toca: es la identidad del ciclo para el usuario.
    `fecha_fin_prevista` es generada y la recalcula Postgres."""
    ciclo.objetivo = objetivo
    ciclo.fecha_inicio = fecha_inicio
    ciclo.semanas = semanas
    await session.flush()
    # fecha_fin_prevista es Computed: el UPDATE la deja expirada (no vino con
    # RETURNING como el INSERT de crear). Sin refrescarla aca, el primer
    # acceso pasa a ser un lazy-load fuera del greenlet async y revienta con
    # MissingGreenlet. Lo toca `validar_espaciado`, que la usa como rango.
    await session.refresh(ciclo, attribute_names=["fecha_fin_prevista"])
    return ciclo


async def cerrar(session: AsyncSession, ciclo: Ciclo, fecha_cierre_real: date) -> Ciclo:
    """Atómico con `estado=cerrado`: sin esto, el CHECK de la tabla
    (fecha_cierre_real IS NULL OR estado = cerrado) rechazaría un cierre
    con fecha pero sin el estado correspondiente."""
    ciclo.fecha_cierre_real = fecha_cierre_real
    ciclo.estado = EstadoCiclo.cerrado
    await session.flush()
    return ciclo
