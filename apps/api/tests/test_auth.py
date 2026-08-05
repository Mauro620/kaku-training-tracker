"""Tests de integración de /auth: login, refresh, logout, /me.

Automatiza los 10 escenarios verificados a mano con curl al cerrar el Paso 1
de Fase 3 (AGENTS.md §3.5: los endpoints llevan test del camino feliz más los
errores declarados).

El endpoint usa la misma `sesion` de conftest.py (savepoint sobre la base de
prueba aislada): se sobreescribe `get_session` para que las mutaciones del
router (rotar el refresh, etc.) se vean dentro del test y desaparezcan con el
rollback de la fixture.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import hashear_password
from app.db.session import get_session
from app.main import app
from app.models import AuthUsuario, Usuario

# email-validator rechaza TLDs reservados (.local, .test); example.com es
# el dominio de RFC 2606 reservado para documentación y pruebas.
EMAIL = "test@example.com"
PASSWORD = "una-password-de-prueba"


@pytest.fixture
async def auth_seed(sesion: AsyncSession) -> AuthUsuario:
    """El seed de conftest.py ya crea un AuthUsuario para el usuario único
    (con el email/password reales de `.env.local`). Se reutiliza esa fila y
    se le pisan las credenciales por unas conocidas, en vez de insertar una
    segunda: `auth_usuario` es 1:1 con `usuario` por PK=FK."""
    usuario_id = await sesion.scalar(select(Usuario.id))
    auth = await sesion.scalar(
        select(AuthUsuario).where(AuthUsuario.usuario_id == usuario_id)
    )
    assert auth is not None, "conftest.py deberia haber sembrado auth_usuario"
    auth.email = EMAIL
    auth.password_hash = hashear_password(PASSWORD)
    auth.refresh_token_hash = None
    auth.refresh_token_expira_en = None
    await sesion.flush()
    return auth


@pytest.fixture
async def cliente_auth(
    sesion: AsyncSession, auth_seed: AuthUsuario
) -> AsyncGenerator[AsyncClient, None]:
    async def _sesion_de_prueba() -> AsyncGenerator[AsyncSession, None]:
        yield sesion

    app.dependency_overrides[get_session] = _sesion_de_prueba
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


async def test_login_devuelve_tokens_y_me_los_reconoce(
    cliente_auth: AsyncClient,
) -> None:
    login = await cliente_auth.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60

    me = await cliente_auth.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200


async def test_login_con_password_incorrecta_devuelve_401(
    cliente_auth: AsyncClient,
) -> None:
    respuesta = await cliente_auth.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": "incorrecta"}
    )
    assert respuesta.status_code == 401


async def test_login_con_email_inexistente_devuelve_401(
    cliente_auth: AsyncClient,
) -> None:
    """No debe distinguirse de una password incorrecta: mismo status y mensaje."""
    respuesta = await cliente_auth.post(
        "/api/v1/auth/login",
        json={"email": "no-existe@example.com", "password": PASSWORD},
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "credenciales invalidas"


async def test_me_sin_token_devuelve_401(cliente_auth: AsyncClient) -> None:
    respuesta = await cliente_auth.get("/api/v1/auth/me")
    assert respuesta.status_code == 401


async def test_me_con_token_adulterado_devuelve_401(cliente_auth: AsyncClient) -> None:
    login = await cliente_auth.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    token_adulterado = login.json()["access_token"][:-1] + "x"

    respuesta = await cliente_auth.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_adulterado}"},
    )
    assert respuesta.status_code == 401


async def test_refresh_rota_el_token_y_el_viejo_deja_de_servir(
    cliente_auth: AsyncClient,
) -> None:
    login = await cliente_auth.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    refresh_viejo = login.json()["refresh_token"]

    primero = await cliente_auth.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_viejo}
    )
    assert primero.status_code == 200
    assert primero.json()["refresh_token"] != refresh_viejo

    segundo = await cliente_auth.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_viejo}
    )
    assert segundo.status_code == 401


async def test_logout_invalida_el_refresh(cliente_auth: AsyncClient) -> None:
    login = await cliente_auth.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    refresh_token = login.json()["refresh_token"]

    logout = await cliente_auth.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout.status_code == 204

    reintento = await cliente_auth.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reintento.status_code == 401


async def test_logout_es_idempotente_con_un_token_desconocido(
    cliente_auth: AsyncClient,
) -> None:
    respuesta = await cliente_auth.post(
        "/api/v1/auth/logout", json={"refresh_token": "token-que-nunca-existio"}
    )
    assert respuesta.status_code == 204
