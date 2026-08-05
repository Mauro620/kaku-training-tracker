from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.main import app

PREFIJO = get_settings().api_v1_prefix


async def test_health_responde_ok_con_la_base_arriba(cliente: AsyncClient) -> None:
    respuesta = await cliente.get(f"{PREFIJO}/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok", "base_de_datos": "ok"}


async def test_health_responde_503_con_la_base_caida(cliente: AsyncClient) -> None:
    """Un health que devuelve 200 con la base caída no sirve para nada."""

    class SesionRota(AsyncSession):
        async def execute(self, *args: object, **kwargs: object) -> object:
            raise OperationalError("SELECT 1", {}, Exception("sin conexión"))

    async def sesion_rota() -> AsyncGenerator[AsyncSession, None]:
        yield SesionRota()

    app.dependency_overrides[get_session] = sesion_rota
    try:
        respuesta = await cliente.get(f"{PREFIJO}/health")
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 503
    assert respuesta.json() == {"status": "degraded", "base_de_datos": "sin_conexion"}


@pytest.fixture(autouse=True)
def _limpiar_overrides() -> AsyncGenerator[None, None]:
    yield
    app.dependency_overrides.clear()
