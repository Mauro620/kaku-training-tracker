"""Tests de integración de la rebanada de Fase 3: sueño, bienestar, hábitos.

Camino feliz + los errores declarados por cada servicio (AGENTS.md §3.5), sin
repetir lo que ya cubre test_esquema.py (rangos, CHECK) ni test_auth.py
(login). `get_usuario_actual` se sobreescribe para no re-probar JWT acá.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import Habito, Usuario


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


# ---------------------------------------------------------------- sueño ----


async def test_registrar_y_leer_sueno(cliente: AsyncClient) -> None:
    payload = {
        "fecha": "2026-08-04",
        "inicio": "2026-08-03T23:30:00-05:00",
        "fin": "2026-08-04T07:00:00-05:00",
        "celular_fuera": True,
    }
    creado = await cliente.post("/api/v1/sueno", json=payload)
    assert creado.status_code == 200
    assert creado.json()["horas_sueno"] == "7.50"

    leido = await cliente.get("/api/v1/sueno/2026-08-04")
    assert leido.status_code == 200
    assert leido.json()["celular_fuera"] is True


async def test_sueno_con_fecha_que_no_coincide_con_fin_devuelve_422(
    cliente: AsyncClient,
) -> None:
    payload = {
        "fecha": "2026-08-05",  # el despertar real es el 4, no el 5
        "inicio": "2026-08-03T23:30:00-05:00",
        "fin": "2026-08-04T07:00:00-05:00",
    }
    respuesta = await cliente.post("/api/v1/sueno", json=payload)
    assert respuesta.status_code == 422


async def test_leer_sueno_de_fecha_sin_registro_devuelve_404(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.get("/api/v1/sueno/2020-01-01")
    assert respuesta.status_code == 404


# ------------------------------------------------------------ bienestar ----


async def test_registrar_y_leer_bienestar(cliente: AsyncClient) -> None:
    payload = {
        "fecha": "2026-08-04",
        "sueno_pobre": 2,
        "fatiga": 3,
        "dolor_muscular": 1,
        "estres": 2,
    }
    creado = await cliente.post("/api/v1/bienestar", json=payload)
    assert creado.status_code == 200
    assert creado.json()["hooper"] == 8

    leido = await cliente.get("/api/v1/bienestar/2026-08-04")
    assert leido.status_code == 200


async def test_leer_bienestar_de_fecha_sin_registro_devuelve_404(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.get("/api/v1/bienestar/2020-01-01")
    assert respuesta.status_code == 404


# --------------------------------------------------------------- hábitos ----


async def test_listar_habitos_devuelve_los_sembrados(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/v1/habitos")
    assert respuesta.status_code == 200
    nombres = {h["nombre"] for h in respuesta.json()}
    assert "creatina" in nombres


async def test_registrar_habito_y_leerlo_por_fecha(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    habito_id = await sesion.scalar(
        select(Habito.id).where(Habito.nombre == "creatina")
    )
    creado = await cliente.post(
        "/api/v1/habitos/registro",
        json={"habito_id": habito_id, "fecha": "2026-08-04", "valor": True},
    )
    assert creado.status_code == 200

    leido = await cliente.get("/api/v1/habitos/registro/2026-08-04")
    assert leido.status_code == 200
    assert any(r["habito_id"] == habito_id and r["valor"] for r in leido.json())


async def test_registrar_habito_inexistente_devuelve_404(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.post(
        "/api/v1/habitos/registro",
        json={"habito_id": 999999, "fecha": "2026-08-04", "valor": True},
    )
    assert respuesta.status_code == 404
