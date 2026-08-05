"""Configuración compartida de tests.

Los valores por defecto apuntan al Postgres de `docker-compose.yml`. Se usan
`setdefault` para que el entorno real (CI, `.env.local`) siempre gane.
"""

import asyncio
import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "rendimiento")
os.environ.setdefault("POSTGRES_USER", "rendimiento")
os.environ.setdefault("POSTGRES_PASSWORD", "rendimiento")
os.environ.setdefault("SEED_USUARIO_NOMBRE", "Test")
os.environ.setdefault("APP_ENV", "test")
# get_settings() tiene @lru_cache: si algo lo llama antes de que esta línea
# corra, el valor queda pegado sin JWT_SECRET_KEY y ningún test de auth puede
# resetearlo mid-flight. Por eso va acá arriba, antes de cualquier import de
# app.*.
os.environ.setdefault("JWT_SECRET_KEY", "clave-de-test-no-usar-en-produccion")

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.seeds.__main__ import sembrar

NOMBRE_USUARIO_SEED = "Test"


@pytest.fixture
async def cliente() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _recrear_base(url_admin: str, nombre: str) -> None:
    motor = create_async_engine(url_admin, isolation_level="AUTOCOMMIT")
    async with motor.connect() as conexion:
        await conexion.execute(text(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)'))
        await conexion.execute(text(f'CREATE DATABASE "{nombre}"'))
    await motor.dispose()


async def _preparar(url: str) -> None:
    motor = create_async_engine(url)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(motor)() as s:
        await sembrar(s, NOMBRE_USUARIO_SEED)
        await s.commit()
    await motor.dispose()


@pytest.fixture(scope="session")
def url_base_de_prueba() -> str:
    """Base limpia por corrida: se crea, se migra y se siembra UNA vez.

    Fixture síncrona a propósito: una async con scope de sesión necesitaría un
    event loop compartido entre fixtures y tests, y no vale la complejidad.
    """
    settings = get_settings()
    nombre = f"{settings.postgres_db}_test"
    asyncio.run(_recrear_base(settings.dsn("postgres"), nombre))
    asyncio.run(_preparar(settings.test_database_url))
    return settings.test_database_url


@pytest.fixture
async def sesion(url_base_de_prueba: str) -> AsyncGenerator[AsyncSession, None]:
    """Cada test corre dentro de una transacción que se revierte al terminar.

    `join_transaction_mode="create_savepoint"` hace que los `commit()` del test
    caigan en un SAVEPOINT: se ven dentro del test y desaparecen con el
    rollback de afuera. Sin esto habría que recrear el esquema en cada test, que
    era lo que hacía la suite tres veces más lenta.
    """
    motor = create_async_engine(url_base_de_prueba)
    async with motor.connect() as conexion:
        transaccion = await conexion.begin()
        s = AsyncSession(
            bind=conexion,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield s
        finally:
            await s.close()
            await transaccion.rollback()
    await motor.dispose()
