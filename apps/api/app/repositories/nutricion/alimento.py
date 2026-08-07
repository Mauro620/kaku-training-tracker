from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alimento


async def listar(session: AsyncSession) -> list[Alimento]:
    resultado = await session.scalars(select(Alimento).order_by(Alimento.nombre))
    return list(resultado.all())


async def listar_por_ids(
    session: AsyncSession, alimento_ids: list[int]
) -> list[Alimento]:
    if not alimento_ids:
        return []
    resultado = await session.scalars(
        select(Alimento).where(Alimento.id.in_(alimento_ids))
    )
    return list(resultado.all())
