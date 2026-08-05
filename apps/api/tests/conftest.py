"""Configuración compartida de tests.

Los valores por defecto apuntan al Postgres de `docker-compose.yml`. Se usan
`setdefault` para que el entorno real (CI, `.env.local`) siempre gane.
"""

import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "rendimiento")
os.environ.setdefault("POSTGRES_USER", "rendimiento")
os.environ.setdefault("POSTGRES_PASSWORD", "rendimiento")
os.environ.setdefault("SEED_USUARIO_NOMBRE", "Test")
os.environ.setdefault("APP_ENV", "test")

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def cliente() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
