"""Persistencia de parametro. Sin reglas de negocio."""

from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Parametro


async def obtener_vigente(session: AsyncSession, clave: str) -> Parametro | None:
    """La fila vigente es la de mayor `vigente_desde <= hoy` (ARCHITECTURE.md §3)."""
    return cast(
        "Parametro | None",
        await session.scalar(
            select(Parametro)
            .where(Parametro.clave == clave, Parametro.vigente_desde <= date.today())
            .order_by(Parametro.vigente_desde.desc())
            .limit(1)
        ),
    )
