"""Lectura de parámetros de negocio, con caché en memoria (ARCHITECTURE.md §3).

Sin invalidación al escribir todavía: no existe un endpoint que escriba
`parametro`, así que no hay nada que invalidar. Se agrega cuando exista.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Parametro
from app.repositories.catalogo import parametro as repo

_cache: dict[str, Parametro] = {}


async def obtener(session: AsyncSession, clave: str) -> Parametro:
    if clave in _cache:
        return _cache[clave]

    parametro = await repo.obtener_vigente(session, clave)
    if parametro is None:
        raise RecursoNoEncontradoError(f"parámetro '{clave}' no existe")

    _cache[clave] = parametro
    return parametro
