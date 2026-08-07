from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TipoTest


async def listar(session: AsyncSession) -> list[TipoTest]:
    resultado = await session.scalars(select(TipoTest).order_by(TipoTest.nombre))
    return list(resultado.all())


async def obtener_por_id(session: AsyncSession, tipo_test_id: int) -> TipoTest | None:
    return await session.get(TipoTest, tipo_test_id)
