"""Tests de integracion de Fase 7: test_fisico (con intentos), medida_corporal
y partido.

Camino feliz + el error declarado por cada servicio, sin repetir lo que ya
cubre test_esquema.py. `get_usuario_actual` se sobreescribe para no re-probar
JWT aca. El caso numerico de `pct_decremento` es el de REGLAS_NEGOCIO §7.
"""

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import TipoSesion, TipoTest, Usuario


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


async def _tipo_test_id(sesion: AsyncSession, codigo: str) -> int:
    tipo_id = await sesion.scalar(select(TipoTest.id).where(TipoTest.codigo == codigo))
    assert tipo_id is not None
    return tipo_id


async def _tipo_sesion_id(sesion: AsyncSession, codigo: str) -> int:
    tipo_id = await sesion.scalar(
        select(TipoSesion.id).where(TipoSesion.codigo == codigo)
    )
    assert tipo_id is not None
    return tipo_id


async def _crear_sesion(cliente: AsyncClient, tipo_sesion_id: int, fecha: str) -> str:
    payload = {
        "id": str(uuid.uuid4()),
        "idempotency_key": str(uuid.uuid4()),
        "fecha": fecha,
        "tipo_sesion_id": tipo_sesion_id,
        "duracion_min": 90,
        "rpe": 6,
    }
    respuesta = await cliente.post("/api/v1/sesiones", json=payload)
    assert respuesta.status_code == 200
    return respuesta.json()["id"]


# ------------------------------------------------------------- test_fisico --


async def test_registrar_test_es_idempotente_y_no_duplica_intentos(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    tipo_id = await _tipo_test_id(sesion, "cmj")
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "fecha": "2026-08-07",
        "tipo_test_id": tipo_id,
        "valores": ["38.5", "40.1", "39.2"],
    }
    primera = await cliente.post("/api/v1/tests", json=payload)
    assert primera.status_code == 200
    assert len(primera.json()["intentos"]) == 3

    segunda = await cliente.post("/api/v1/tests", json=payload)
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primera.json()["id"]
    assert len(segunda.json()["intentos"]) == 3


async def test_registrar_test_con_tipo_inexistente_devuelve_404(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-07",
            "tipo_test_id": 9999,
            "valores": ["10.0"],
        },
    )
    assert respuesta.status_code == 404


async def test_obtener_test_inexistente_devuelve_404(cliente: AsyncClient) -> None:
    respuesta = await cliente.get(f"/api/v1/tests/{uuid.uuid4()}")
    assert respuesta.status_code == 404


async def test_resultado_rsa_calcula_pct_decremento(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """REGLAS_NEGOCIO §7: tiempos [4.20, 4.28, 4.35, 4.41, 4.52, 4.60] ->
    mejor 4.20, suma 26.36, pct_decremento ~= 4.603."""
    tipo_id = await _tipo_test_id(sesion, "rsa_30m")
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "fecha": "2026-08-07",
        "tipo_test_id": tipo_id,
        "valores": ["4.20", "4.28", "4.35", "4.41", "4.52", "4.60"],
    }
    creado = await cliente.post("/api/v1/tests", json=payload)
    assert creado.status_code == 200
    test_id = creado.json()["id"]

    resultado = await cliente.get(f"/api/v1/tests/{test_id}/resultado")
    assert resultado.status_code == 200
    cuerpo = resultado.json()
    assert cuerpo["mejor"] == "4.200"
    pct = Decimal(cuerpo["pct_decremento"])
    assert abs(pct - Decimal("4.603")) < Decimal("0.001")


async def test_resultado_con_menos_de_4_intentos_pct_decremento_es_none(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    tipo_id = await _tipo_test_id(sesion, "rsa_30m")
    creado = await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-07",
            "tipo_test_id": tipo_id,
            "valores": ["4.20", "4.28", "4.35"],
        },
    )
    test_id = creado.json()["id"]

    resultado = await cliente.get(f"/api/v1/tests/{test_id}/resultado")
    assert resultado.json()["pct_decremento"] is None


async def test_pct_cambio_es_none_en_el_primer_test_del_tipo(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    tipo_id = await _tipo_test_id(sesion, "cmj")
    creado = await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-01",
            "tipo_test_id": tipo_id,
            "valores": ["38.0"],
        },
    )
    test_id = creado.json()["id"]

    resultado = await cliente.get(f"/api/v1/tests/{test_id}/resultado")
    assert resultado.json()["pct_cambio"] is None


async def test_pct_cambio_mejor_es_mayor_true_sube_si_el_salto_es_mas_alto(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """cmj: mejor_es_mayor=True. Segundo test con salto mas alto -> pct_cambio > 0."""
    tipo_id = await _tipo_test_id(sesion, "cmj")
    await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-01",
            "tipo_test_id": tipo_id,
            "valores": ["38.0"],
        },
    )
    segundo = await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-07",
            "tipo_test_id": tipo_id,
            "valores": ["41.8"],
        },
    )
    test_id = segundo.json()["id"]

    resultado = await cliente.get(f"/api/v1/tests/{test_id}/resultado")
    pct = Decimal(resultado.json()["pct_cambio"])
    assert pct == Decimal("10")  # (41.8-38)/38 * 100


async def test_pct_cambio_mejor_es_mayor_false_sube_si_el_tiempo_baja(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """sprint_10m: mejor_es_mayor=False. Segundo test mas rapido -> pct_cambio > 0."""
    tipo_id = await _tipo_test_id(sesion, "sprint_10m")
    await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-01",
            "tipo_test_id": tipo_id,
            "valores": ["1.80"],
        },
    )
    segundo = await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-07",
            "tipo_test_id": tipo_id,
            "valores": ["1.71"],
        },
    )
    test_id = segundo.json()["id"]

    resultado = await cliente.get(f"/api/v1/tests/{test_id}/resultado")
    pct = Decimal(resultado.json()["pct_cambio"])
    assert pct == Decimal("5")  # (1.80-1.71)/1.80 * 100


async def test_eliminar_test_fisico_borra_intentos(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    tipo_id = await _tipo_test_id(sesion, "cmj")
    creado = await cliente.post(
        "/api/v1/tests",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-07",
            "tipo_test_id": tipo_id,
            "valores": ["38.0"],
        },
    )
    test_id = creado.json()["id"]

    eliminado = await cliente.delete(f"/api/v1/tests/{test_id}")
    assert eliminado.status_code == 204

    releido = await cliente.get(f"/api/v1/tests/{test_id}")
    assert releido.status_code == 404


async def test_eliminar_test_inexistente_devuelve_404(cliente: AsyncClient) -> None:
    respuesta = await cliente.delete(f"/api/v1/tests/{uuid.uuid4()}")
    assert respuesta.status_code == 404


# --------------------------------------------------------- medida_corporal --


async def test_registrar_medida_upsert_por_fecha(cliente: AsyncClient) -> None:
    primera = await cliente.post(
        "/api/v1/medidas", json={"fecha": "2026-08-07", "peso_kg": "78.50"}
    )
    assert primera.status_code == 200
    assert primera.json()["peso_kg"] == "78.50"

    segunda = await cliente.post(
        "/api/v1/medidas",
        json={"fecha": "2026-08-07", "peso_kg": "78.10", "fc_reposo": 58},
    )
    assert segunda.status_code == 200
    assert segunda.json()["peso_kg"] == "78.10"
    assert segunda.json()["fc_reposo"] == 58
    assert segunda.json()["id"] == primera.json()["id"]

    listado = await cliente.get("/api/v1/medidas")
    assert len(listado.json()) == 1


# ----------------------------------------------------------------- partido --


async def test_registrar_partido_vinculado_a_sesion_es_idempotente(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    tipo_sesion_id = await _tipo_sesion_id(sesion, "partido")
    sesion_id = await _crear_sesion(cliente, tipo_sesion_id, "2026-08-07")

    payload = {
        "sesion_id": sesion_id,
        "rival": "Millonarios sub-20",
        "minutos_jugados": 75,
        "goles": 1,
        "asistencias": 2,
    }
    primero = await cliente.post("/api/v1/partidos", json=payload)
    assert primero.status_code == 200
    assert primero.json()["sesion_id"] == sesion_id

    segundo = await cliente.post("/api/v1/partidos", json=payload)
    assert segundo.status_code == 200
    assert segundo.json()["id"] == primero.json()["id"]

    listado = await cliente.get("/api/v1/partidos")
    assert len(listado.json()) == 1


async def test_registrar_partido_con_sesion_inexistente_devuelve_404(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.post(
        "/api/v1/partidos",
        json={"sesion_id": str(uuid.uuid4()), "minutos_jugados": 60},
    )
    assert respuesta.status_code == 404


async def test_obtener_partido_inexistente_devuelve_404(cliente: AsyncClient) -> None:
    respuesta = await cliente.get(f"/api/v1/partidos/{uuid.uuid4()}")
    assert respuesta.status_code == 404
