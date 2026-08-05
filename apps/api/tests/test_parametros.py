"""Tests de integración de /parametros. Camino feliz + el 404 declarado."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import Usuario


@pytest.fixture
async def cliente(sesion: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    usuario = await sesion.scalar(select(Usuario))

    async def _sesion_de_prueba() -> AsyncGenerator[AsyncSession, None]:
        yield sesion

    app.dependency_overrides[get_session] = _sesion_de_prueba
    app.dependency_overrides[get_usuario_actual] = lambda: usuario
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


async def test_leer_parametro_sembrado(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/v1/parametros/dia_registro_hora_corte")
    assert respuesta.status_code == 200
    assert respuesta.json()["valor"] == "4.0000"


async def test_leer_parametro_inexistente_devuelve_404(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/v1/parametros/no-existe")
    assert respuesta.status_code == 404
