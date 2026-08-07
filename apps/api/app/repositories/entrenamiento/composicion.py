"""Persistencia de ciclo_semana_composicion. Sin reglas de negocio."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CicloSemanaComposicion


async def reemplazar(
    session: AsyncSession,
    ciclo_semana_id: int,
    items: list[tuple[int, int]],
) -> list[CicloSemanaComposicion]:
    """Borra la composición existente de la semana y crea la nueva
    completa. No es upsert incremental a propósito: declarar la semana
    entera de una vez evita que queden filas viejas de un tipo_sesion que
    ya no forma parte de la composición."""
    await session.execute(
        delete(CicloSemanaComposicion).where(
            CicloSemanaComposicion.ciclo_semana_id == ciclo_semana_id
        )
    )
    nuevas = [
        CicloSemanaComposicion(
            ciclo_semana_id=ciclo_semana_id,
            tipo_sesion_id=tipo_sesion_id,
            cantidad_objetivo=cantidad_objetivo,
        )
        for tipo_sesion_id, cantidad_objetivo in items
    ]
    session.add_all(nuevas)
    await session.flush()
    return nuevas


async def listar_por_semana(
    session: AsyncSession, ciclo_semana_id: int
) -> list[CicloSemanaComposicion]:
    resultado = await session.scalars(
        select(CicloSemanaComposicion)
        .where(CicloSemanaComposicion.ciclo_semana_id == ciclo_semana_id)
        .order_by(CicloSemanaComposicion.tipo_sesion_id)
    )
    return list(resultado.all())


async def eliminar_por_semana(session: AsyncSession, ciclo_semana_id: int) -> None:
    await session.execute(
        delete(CicloSemanaComposicion).where(
            CicloSemanaComposicion.ciclo_semana_id == ciclo_semana_id
        )
    )
