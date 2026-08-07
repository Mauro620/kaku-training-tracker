from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TipoSesion


async def listar(session: AsyncSession) -> list[TipoSesion]:
    resultado = await session.scalars(select(TipoSesion).order_by(TipoSesion.id))
    return list(resultado.all())
