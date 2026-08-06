from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ZonaCorporal


async def listar(session: AsyncSession) -> list[ZonaCorporal]:
    resultado = await session.scalars(
        select(ZonaCorporal).order_by(ZonaCorporal.nombre)
    )
    return list(resultado.all())
