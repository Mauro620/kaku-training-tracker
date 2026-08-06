"""Lectura de catálogos de entrenamiento. Sin reglas de negocio: el usuario
no crea valores, solo lee. El service existe igual para que el router nunca
importe el repositorio directo (ARCHITECTURE.md §2)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ejercicio, TipoSesion, ZonaCorporal
from app.repositories.catalogo import ejercicio as repo_ejercicio
from app.repositories.catalogo import tipo_sesion as repo_tipo_sesion
from app.repositories.catalogo import zona_corporal as repo_zona_corporal


async def listar_tipos_sesion(session: AsyncSession) -> list[TipoSesion]:
    return await repo_tipo_sesion.listar(session)


async def listar_ejercicios(session: AsyncSession) -> list[Ejercicio]:
    return await repo_ejercicio.listar(session)


async def listar_zonas_corporales(session: AsyncSession) -> list[ZonaCorporal]:
    return await repo_zona_corporal.listar(session)
