from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ejercicio


async def listar(session: AsyncSession) -> list[Ejercicio]:
    resultado = await session.scalars(select(Ejercicio).order_by(Ejercicio.nombre))
    return list(resultado.all())
