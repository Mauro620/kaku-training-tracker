"""Reglas de negocio de Alimento (Fase 6, ROADMAP §6).

El catalogo es un universo cerrado: no hay Create/Update, los alimentos
se siembran en `app.seeds/alimentos.py`. Por eso este modulo solo expone
el `listar` de passthrough.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alimento
from app.repositories import nutricion as repo


async def listar(session: AsyncSession) -> list[Alimento]:
    """Lee el catalogo entero. Ordenado por nombre para que el selector de
    la UI sea estable (los alimentos no cambian de nombre seguido)."""
    return await repo.listar_alimentos(session)
