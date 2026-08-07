from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ejercicio
from app.models.enums import CargaLumbar, TipoMedicion


async def listar(session: AsyncSession) -> list[Ejercicio]:
    resultado = await session.scalars(select(Ejercicio).order_by(Ejercicio.nombre))
    return list(resultado.all())


async def listar_por_ids(session: AsyncSession, ids: list[int]) -> list[Ejercicio]:
    if not ids:
        return []
    resultado = await session.scalars(select(Ejercicio).where(Ejercicio.id.in_(ids)))
    return list(resultado.all())


async def obtener_por_nombre(session: AsyncSession, nombre: str) -> Ejercicio | None:
    return cast(
        "Ejercicio | None",
        await session.scalar(select(Ejercicio).where(Ejercicio.nombre == nombre)),
    )


async def crear(
    session: AsyncSession, *, nombre: str, tipo_medicion: TipoMedicion
) -> Ejercicio:
    """Unico catalogo con creacion de usuario (REGLAS_NEGOCIO §15): el
    universo de ejercicios de una rutina real es abierto, a diferencia de
    tipo_sesion o zona_corporal. carga_lumbar/tipo_sesion_id quedan en su
    default (baja/NULL): el usuario no los declara al crear inline."""
    ejercicio = Ejercicio(
        nombre=nombre, tipo_medicion=tipo_medicion, carga_lumbar=CargaLumbar.baja
    )
    session.add(ejercicio)
    await session.flush()
    return ejercicio
