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


async def test_sueno_ultimos_n_dias_devuelve_ventana(
    cliente: AsyncClient,
) -> None:
    """H3 de la revision de UI: la pantalla Hoy pide 14 dias para graficar
    la grilla y calcular la deuda 7d. El endpoint acepta un query param
    `dias` (default 14, max 60) y devuelve los registros del rango, ordenados
    del mas reciente al mas viejo."""
    # 3 noches, cada una con su propia fecha de despertar (el modelo
    # es unique por (usuario_id, fecha_del_despertar)).
    noches = [
        ("2026-08-01", "2026-07-31T23:30:00-05:00", "2026-08-01T07:00:00-05:00"),
        ("2026-08-02", "2026-08-01T23:30:00-05:00", "2026-08-02T07:00:00-05:00"),
        ("2026-08-04", "2026-08-03T23:30:00-05:00", "2026-08-04T07:00:00-05:00"),
    ]
    for fecha, inicio, fin in noches:
        await cliente.post(
            "/api/v1/sueno",
            json={
                "fecha": fecha,
                "inicio": inicio,
                "fin": fin,
                "celular_fuera": True,
            },
        )

    # Pido 14 dias, solo 3 deberian aparecer (solo los que tienen fila).
    respuesta = await cliente.get("/api/v1/sueno/ultimos?dias=14")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)
    assert len(cuerpo) == 3
    # Orden: descendente (mas reciente primero).
    assert cuerpo[0]["fecha"] == "2026-08-04"
    assert cuerpo[1]["fecha"] == "2026-08-02"
    assert cuerpo[2]["fecha"] == "2026-08-01"
    # Cada uno trae horas_sueno calculado por la base.
    for item in cuerpo:
        assert item["horas_sueno"] == "7.50"


async def test_sueno_ultimos_dias_param_valida_rango(
    cliente: AsyncClient,
) -> None:
    """El parametro `dias` tiene cota 1..60; fuera de rango es 422."""
    assert (await cliente.get("/api/v1/sueno/ultimos?dias=0")).status_code == 422
    assert (await cliente.get("/api/v1/sueno/ultimos?dias=61")).status_code == 422
    assert (await cliente.get("/api/v1/sueno/ultimos?dias=14")).status_code == 200


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


# ----------------------------------------- Cierre de semana (C) -----


async def test_cierre_semana_devuelve_data_cruda_por_dia(
    cliente: AsyncClient,
) -> None:
    """C de la revision de UI: el endpoint devuelve la data cruda de
    cada una de las 5 dimensiones por dia. La UI arma el grid 5x7 con
    flags cumplidos/incumplidos/sin-dato a partir de estos datos."""
    # Creo un registro de cada dimension en un dia conocido.
    fecha = "2026-08-04"
    # Sueno
    await cliente.post(
        "/api/v1/sueno",
        json={
            "fecha": fecha,
            "inicio": "2026-08-03T23:30:00-05:00",
            "fin": "2026-08-04T07:00:00-05:00",
            "celular_fuera": True,
        },
    )
    # Bienestar
    await cliente.post(
        "/api/v1/bienestar",
        json={
            "fecha": fecha,
            "sueno_pobre": 2,
            "fatiga": 3,
            "dolor_muscular": 1,
            "estres": 2,
        },
    )
    # Hidratacion
    await cliente.post(
        "/api/v1/hidratacion",
        json={"fecha": fecha, "cantidad_ml": 3500},
    )
    # Sesion
    await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid4()),
            "idempotency_key": str(uuid4()),
            "fecha": fecha,
            "tipo_sesion_id": 1,
            "duracion_min": 60,
            "rpe": 6,
            "bloques": [],
        },
    )
    respuesta = await cliente.get("/api/v1/semana?desde=2026-08-01&hasta=2026-08-07")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["dias"]) == 7

    # El dia 2026-08-04 tiene todos los datos.
    dia_con_dato = next(d for d in cuerpo["dias"] if d["fecha"] == "2026-08-04")
    assert float(dia_con_dato["sueno"]["horas"]) == 7.5
    assert float(dia_con_dato["sueno"]["objetivo_h"]) == 7.0
    assert dia_con_dato["sesion"]["registrada"] is True
    assert dia_con_dato["hidratacion"]["ml_totales"] == 3500
    assert dia_con_dato["hidratacion"]["objetivo_ml"] == 3000
    assert dia_con_dato["habitos"]["marcados"] == 0
    assert dia_con_dato["bienestar"]["registrado"] is True

    # Un dia sin datos: todos los null donde corresponda.
    dia_vacio = next(d for d in cuerpo["dias"] if d["fecha"] == "2026-08-01")
    assert dia_vacio["sueno"]["horas"] is None
    assert dia_vacio["sesion"]["registrada"] is False
    assert dia_vacio["hidratacion"]["ml_totales"] is None
    assert dia_vacio["bienestar"]["registrado"] is False


async def test_cierre_semana_rango_mayor_a_31_dias_devuelve_422(
    cliente: AsyncClient,
) -> None:
    """El cap de 31 dias esta para no tirar queries absurdas; un mes
    alcanza para esta pantalla."""
    respuesta = await cliente.get("/api/v1/semana?desde=2026-01-01&hasta=2026-02-15")
    assert respuesta.status_code == 422


async def test_cierre_semana_rango_invertido_devuelve_422(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.get("/api/v1/semana?desde=2026-08-07&hasta=2026-08-01")
    assert respuesta.status_code == 422
