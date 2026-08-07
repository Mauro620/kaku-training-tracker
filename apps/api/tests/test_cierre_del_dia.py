"""Tests de integración de la rebanada de Fase 3: sueño, bienestar, hábitos,
hidratación.

Camino feliz + los errores declarados por cada servicio (AGENTS.md §3.5), sin
repetir lo que ya cubre test_esquema.py (rangos, CHECK) ni test_auth.py
(login). `get_usuario_actual` se sobreescribe para no re-probar JWT acá.

Los tests de idempotencia son de Fase 5: el ROADMAP §5 pide "Test que envía
el mismo evento tres veces y verifica una sola fila".
"""

from collections.abc import AsyncGenerator
from datetime import date as _date
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import Habito, RegistroBienestar, RegistroSueno, Usuario


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


async def test_hidratacion_no_aparece_en_habitos(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/v1/habitos")
    nombres = {h["nombre"] for h in respuesta.json()}
    assert "hidratacion" not in nombres


# ----------------------------------------------------------- hidratación ----


async def test_cada_registro_de_hidratacion_suma_al_total(
    cliente: AsyncClient,
) -> None:
    for _ in range(3):
        respuesta = await cliente.post(
            "/api/v1/hidratacion", json={"fecha": "2026-08-04", "cantidad_ml": 750}
        )
    assert respuesta.status_code == 200
    assert respuesta.json()["ml_totales"] == 2250

    leido = await cliente.get("/api/v1/hidratacion/2026-08-04")
    assert leido.json()["ml_totales"] == 2250


async def test_leer_hidratacion_de_fecha_sin_registro_devuelve_404(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.get("/api/v1/hidratacion/2020-01-01")
    assert respuesta.status_code == 404


# ----------------------------------------------- idempotencia (Fase 5) -----


async def test_sueno_con_misma_idempotency_key_devuelve_misma_fila(
    cliente: AsyncClient,
) -> None:
    """ROADMAP §5: el mismo POST tres veces con misma key, una sola fila."""
    key = str(uuid4())
    payload = {
        "fecha": "2026-08-05",
        "inicio": "2026-08-04T23:30:00Z",
        "fin": "2026-08-05T07:00:00Z",
        "idempotency_key": key,
    }
    ids: set[int] = set()
    for _ in range(3):
        respuesta = await cliente.post("/api/v1/sueno", json=payload)
        assert respuesta.status_code == 200
        ids.add(respuesta.json()["id"])
    assert len(ids) == 1


async def test_bienestar_con_misma_idempotency_key_devuelve_misma_fila(
    cliente: AsyncClient,
) -> None:
    key = str(uuid4())
    payload = {
        "fecha": "2026-08-05",
        "sueno_pobre": 2,
        "fatiga": 3,
        "dolor_muscular": 1,
        "estres": 2,
        "idempotency_key": key,
    }
    ids: set[int] = set()
    for _ in range(3):
        respuesta = await cliente.post("/api/v1/bienestar", json=payload)
        assert respuesta.status_code == 200
        ids.add(respuesta.json()["id"])
    assert len(ids) == 1


async def test_habito_con_misma_idempotency_key_devuelve_misma_fila(
    cliente: AsyncClient,
) -> None:
    habito_id = (await cliente.get("/api/v1/habitos")).json()[0]["id"]
    key = str(uuid4())
    payload = {
        "habito_id": habito_id,
        "fecha": "2026-08-05",
        "valor": True,
        "idempotency_key": key,
    }
    ids: set[tuple[int, str]] = set()
    for _ in range(3):
        respuesta = await cliente.post("/api/v1/habitos/registro", json=payload)
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        ids.add((cuerpo["habito_id"], cuerpo["fecha"]))
    assert len(ids) == 1


async def test_hidratacion_con_misma_idempotency_key_no_suma_dos_veces(
    cliente: AsyncClient,
) -> None:
    """ROADMAP §5: idempotencia de hidratacion. La cola que reintenta con
    la misma key no debe sumar `cantidad_ml` dos veces."""
    key = str(uuid4())
    payload = {
        "fecha": "2026-08-05",
        "cantidad_ml": 750,
        "idempotency_key": key,
    }
    for _ in range(3):
        respuesta = await cliente.post("/api/v1/hidratacion", json=payload)
        assert respuesta.status_code == 200
    assert respuesta.json()["ml_totales"] == 750

    # Otro tap con key distinta debe sumar.
    otro = await cliente.post(
        "/api/v1/hidratacion",
        json={
            "fecha": "2026-08-05",
            "cantidad_ml": 500,
            "idempotency_key": str(uuid4()),
        },
    )
    assert otro.status_code == 200
    assert otro.json()["ml_totales"] == 1250


async def test_hidratacion_reintento_de_segundo_tap_no_suma_dos_veces(
    cliente: AsyncClient,
) -> None:
    """Regresion: la key de un tap que NO es el primero del dia tambien
    tiene que persistirse, si no un reintento de ESE tap especifico vuelve
    a sumar (bug real: la key solo quedaba grabada en el primer tap)."""
    fecha = "2026-08-06"
    await cliente.post(
        "/api/v1/hidratacion",
        json={"fecha": fecha, "cantidad_ml": 750, "idempotency_key": str(uuid4())},
    )

    key_segundo_tap = str(uuid4())
    payload_segundo_tap = {
        "fecha": fecha,
        "cantidad_ml": 500,
        "idempotency_key": key_segundo_tap,
    }
    for _ in range(3):
        respuesta = await cliente.post("/api/v1/hidratacion", json=payload_segundo_tap)
        assert respuesta.status_code == 200
    assert respuesta.json()["ml_totales"] == 1250


async def test_molestia_con_misma_idempotency_key_devuelve_misma_fila(
    cliente: AsyncClient,
) -> None:
    key = str(uuid4())
    payload = {
        "fecha": "2026-08-05",
        "zona_id": 1,
        "intensidad": 4,
        "nota": "muslo",
        "idempotency_key": key,
    }
    ids: set[int] = set()
    for _ in range(3):
        respuesta = await cliente.post("/api/v1/molestias", json=payload)
        assert respuesta.status_code == 200
        ids.add(respuesta.json()["id"])
    assert len(ids) == 1


async def test_sueno_con_key_distinta_actualiza_datos(
    cliente: AsyncClient,
) -> None:
    """La deduplicacion es por `idempotency_key`, no por fecha. Dos POSTs con
    keys distintas y misma fecha actualizan los datos."""
    payload_base = {
        "fecha": "2026-08-06",
        "inicio": "2026-08-05T23:30:00Z",
        "fin": "2026-08-06T07:00:00Z",
    }
    primera = await cliente.post(
        "/api/v1/sueno",
        json={**payload_base, "idempotency_key": str(uuid4())},
    )
    assert primera.status_code == 200
    id_inicial = primera.json()["id"]

    segunda = await cliente.post(
        "/api/v1/sueno",
        json={
            **payload_base,
            "idempotency_key": str(uuid4()),
            "celular_fuera": True,
        },
    )
    assert segunda.status_code == 200
    assert segunda.json()["id"] == id_inicial
    assert segunda.json()["celular_fuera"] is True


async def test_sueno_sin_idempotency_key_sigue_siendo_upsert(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """El `idempotency_key` es opcional: el upsert por (usuario_id, fecha)
    sigue siendo el camino por defecto (backfill Fase 9, Notion)."""
    payload = {
        "fecha": "2026-08-07",
        "inicio": "2026-08-06T23:30:00Z",
        "fin": "2026-08-07T07:00:00Z",
    }
    for _ in range(2):
        respuesta = await cliente.post("/api/v1/sueno", json=payload)
        assert respuesta.status_code == 200
    total = await sesion.scalar(
        select(RegistroSueno).where(RegistroSueno.fecha == _date(2026, 8, 7))
    )
    assert total is not None
    assert total.idempotency_key is None


async def test_bienestar_sin_idempotency_key_sigue_siendo_upsert(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    payload = {
        "fecha": "2026-08-07",
        "sueno_pobre": 2,
        "fatiga": 3,
        "dolor_muscular": 1,
        "estres": 2,
    }
    for _ in range(2):
        respuesta = await cliente.post("/api/v1/bienestar", json=payload)
        assert respuesta.status_code == 200
    total = await sesion.scalar(
        select(RegistroBienestar).where(RegistroBienestar.fecha == _date(2026, 8, 7))
    )
    assert total is not None
    assert total.idempotency_key is None
