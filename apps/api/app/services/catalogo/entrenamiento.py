"""Lectura de catálogos de entrenamiento. Sin reglas de negocio: el usuario
no crea valores, solo lee. El service existe igual para que el router nunca
importe el repositorio directo (ARCHITECTURE.md §2).

`ejercicio` es la excepción (REGLAS_NEGOCIO §15): el único catálogo que el
usuario puede ampliar, porque el universo de ejercicios de una rutina real
es abierto."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvarianteDeNegocioError
from app.models import Ejercicio, TipoSesion, TipoTest, ZonaCorporal
from app.models.enums import TipoMedicion
from app.repositories.catalogo import ejercicio as repo_ejercicio
from app.repositories.catalogo import tipo_sesion as repo_tipo_sesion
from app.repositories.catalogo import tipo_test as repo_tipo_test
from app.repositories.catalogo import zona_corporal as repo_zona_corporal


async def listar_tipos_sesion(session: AsyncSession) -> list[TipoSesion]:
    return await repo_tipo_sesion.listar(session)


async def listar_ejercicios(session: AsyncSession) -> list[Ejercicio]:
    return await repo_ejercicio.listar(session)


async def crear_ejercicio(
    session: AsyncSession, nombre: str, tipo_medicion: TipoMedicion
) -> Ejercicio:
    existente = await repo_ejercicio.obtener_por_nombre(session, nombre)
    if existente is not None:
        raise InvarianteDeNegocioError(f"ya existe un ejercicio llamado '{nombre}'")
    ejercicio = await repo_ejercicio.crear(
        session, nombre=nombre, tipo_medicion=tipo_medicion
    )
    await session.commit()
    await session.refresh(ejercicio)
    return ejercicio


async def listar_zonas_corporales(session: AsyncSession) -> list[ZonaCorporal]:
    return await repo_zona_corporal.listar(session)


async def listar_tipos_test(session: AsyncSession) -> list[TipoTest]:
    return await repo_tipo_test.listar(session)
