"""Tests de integración de la rebanada R1+R2 de Fase 4: sesion (idempotencia),
molestia, catalogos, ciclo/ciclo_semana/composicion/cumplimiento y sesion_plan
con validación de espaciado (REGLAS_NEGOCIO §13).

Camino feliz + el error declarado por cada servicio, sin repetir lo que ya
cubre test_esquema.py. `get_usuario_actual` se sobreescribe para no re-probar
JWT acá.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import Ejercicio, TipoSesion, Usuario


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


async def _tipo_sesion_id(sesion: AsyncSession, codigo: str) -> int:
    tipo_id = await sesion.scalar(
        select(TipoSesion.id).where(TipoSesion.codigo == codigo)
    )
    assert tipo_id is not None
    return tipo_id


async def _ejercicio_de_tipo(sesion: AsyncSession, tipo_sesion_id: int) -> int:
    ejercicio_id = await sesion.scalar(
        select(Ejercicio.id).where(Ejercicio.tipo_sesion_id == tipo_sesion_id)
    )
    assert ejercicio_id is not None
    return ejercicio_id


# ------------------------------------------------------------------ sesion --


async def test_crear_sesion_es_idempotente_y_no_duplica_series(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    tipo_id = await _tipo_sesion_id(sesion, "resistencia")
    ejercicio_id = await sesion.scalar(select(Ejercicio.id))
    payload = {
        "id": str(uuid.uuid4()),
        "idempotency_key": str(uuid.uuid4()),
        "fecha": "2026-08-04",
        "tipo_sesion_id": tipo_id,
        "duracion_min": 60,
        "rpe": 5,
        "series": [
            {"ejercicio_id": ejercicio_id, "orden": 0, "series": 3, "reps": 10},
        ],
    }
    primera = await cliente.post("/api/v1/sesiones", json=payload)
    assert primera.status_code == 200
    assert len(primera.json()["series"]) == 1

    segunda = await cliente.post("/api/v1/sesiones", json=payload)
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primera.json()["id"]
    assert len(segunda.json()["series"]) == 1

    listado = await cliente.get("/api/v1/sesiones", params={"fecha": "2026-08-04"})
    assert len(listado.json()) == 1


# --------------------------------------------------------------- molestia --


async def test_molestia_post_es_upsert_por_fecha_y_zona(cliente: AsyncClient) -> None:
    payload = {"fecha": "2026-08-04", "zona_id": 1, "intensidad": 2}
    await cliente.post("/api/v1/molestias", json=payload)
    actualizada = await cliente.post(
        "/api/v1/molestias", json={**payload, "intensidad": 4}
    )
    assert actualizada.status_code == 200

    listado = await cliente.get("/api/v1/molestias", params={"fecha": "2026-08-04"})
    assert len(listado.json()) == 1
    assert listado.json()[0]["intensidad"] == 4


# -------------------------------------------------------------- catalogos --


async def test_catalogos_devuelven_los_sembrados(cliente: AsyncClient) -> None:
    tipos = await cliente.get("/api/v1/catalogos/tipos-sesion")
    assert "fuerza" in {t["codigo"] for t in tipos.json()}

    zonas = await cliente.get("/api/v1/catalogos/zonas-corporales")
    assert zonas.status_code == 200
    assert len(zonas.json()) > 0

    ejercicios = await cliente.get("/api/v1/catalogos/ejercicios")
    assert ejercicios.status_code == 200
    assert len(ejercicios.json()) > 0


# ------------------------------------------------------------------ ciclo --


async def test_crear_ciclo_calcula_fecha_fin_prevista(cliente: AsyncClient) -> None:
    payload = {
        "numero": 1,
        "objetivo": "Pretemporada",
        "fecha_inicio": "2026-08-03",
        "semanas": 4,
    }
    creado = await cliente.post("/api/v1/ciclos", json=payload)
    assert creado.status_code == 200
    assert creado.json()["fecha_fin_prevista"] == "2026-08-30"
    assert creado.json()["fecha_cierre_real"] is None


async def test_obtener_ciclo_inexistente_devuelve_404(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/v1/ciclos/999999")
    assert respuesta.status_code == 404


async def test_cerrar_ciclo_marca_estado_y_fecha(cliente: AsyncClient) -> None:
    creado = await cliente.post(
        "/api/v1/ciclos",
        json={
            "numero": 1,
            "objetivo": "Pretemporada",
            "fecha_inicio": "2026-08-03",
            "semanas": 4,
        },
    )
    ciclo_id = creado.json()["id"]

    cerrado = await cliente.post(
        f"/api/v1/ciclos/{ciclo_id}/cerrar", json={"fecha_cierre_real": "2026-08-17"}
    )
    assert cerrado.status_code == 200
    assert cerrado.json()["estado"] == "cerrado"
    assert cerrado.json()["fecha_cierre_real"] == "2026-08-17"


# -------------------------------------------------- semana y composicion --


async def test_reemplazar_composicion_reemplaza_todo(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    ciclo = await cliente.post(
        "/api/v1/ciclos",
        json={
            "numero": 1,
            "objetivo": "Pretemporada",
            "fecha_inicio": "2026-08-03",
            "semanas": 4,
        },
    )
    ciclo_id = ciclo.json()["id"]
    semana = await cliente.post(
        f"/api/v1/ciclos/{ciclo_id}/semanas",
        json={"numero": 1, "fase": "carga", "volumen_pct": 100},
    )
    semana_id = semana.json()["id"]

    fuerza_id = await _tipo_sesion_id(sesion, "fuerza")
    resistencia_id = await _tipo_sesion_id(sesion, "resistencia")

    primer_reemplazo = await cliente.put(
        f"/api/v1/ciclos/semanas/{semana_id}/composicion",
        json={
            "items": [
                {"tipo_sesion_id": fuerza_id, "cantidad_objetivo": 2},
                {"tipo_sesion_id": resistencia_id, "cantidad_objetivo": 1},
            ]
        },
    )
    assert len(primer_reemplazo.json()) == 2

    segundo_reemplazo = await cliente.put(
        f"/api/v1/ciclos/semanas/{semana_id}/composicion",
        json={"items": [{"tipo_sesion_id": resistencia_id, "cantidad_objetivo": 1}]},
    )
    assert len(segundo_reemplazo.json()) == 1
    assert segundo_reemplazo.json()[0]["tipo_sesion_id"] == resistencia_id


async def test_cumplimiento_cuenta_sesiones_reales_no_sesion_plan(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    ciclo = await cliente.post(
        "/api/v1/ciclos",
        json={
            "numero": 1,
            "objetivo": "Pretemporada",
            "fecha_inicio": "2026-08-03",
            "semanas": 4,
        },
    )
    ciclo_id = ciclo.json()["id"]
    semana = await cliente.post(
        f"/api/v1/ciclos/{ciclo_id}/semanas",
        json={"numero": 1, "fase": "carga", "volumen_pct": 100},
    )
    semana_id = semana.json()["id"]

    fuerza_id = await _tipo_sesion_id(sesion, "fuerza")
    resistencia_id = await _tipo_sesion_id(sesion, "resistencia")

    await cliente.put(
        f"/api/v1/ciclos/semanas/{semana_id}/composicion",
        json={
            "items": [
                {"tipo_sesion_id": fuerza_id, "cantidad_objetivo": 2},
                {"tipo_sesion_id": resistencia_id, "cantidad_objetivo": 1},
            ]
        },
    )

    # Sesion real de resistencia dentro de la semana (2026-08-03..09): cuenta.
    await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid.uuid4()),
            "idempotency_key": str(uuid.uuid4()),
            "fecha": "2026-08-04",
            "tipo_sesion_id": resistencia_id,
            "duracion_min": 40,
            "rpe": 4,
        },
    )
    # Plan de fuerza (no ejecutado): NO cuenta como hecho.
    await cliente.post(
        "/api/v1/planes",
        json={"ciclo_semana_id": semana_id, "tipo_sesion_id": fuerza_id},
    )

    cumplimiento = await cliente.get(f"/api/v1/ciclos/semanas/{semana_id}/cumplimiento")
    assert cumplimiento.status_code == 200
    por_tipo = {item["tipo_sesion_id"]: item for item in cumplimiento.json()}
    assert por_tipo[resistencia_id]["hecho"] == 1
    assert por_tipo[resistencia_id]["cumplido"] is True
    assert por_tipo[fuerza_id]["hecho"] == 0
    assert por_tipo[fuerza_id]["cumplido"] is False


# ---------------------------------------------------- sesion_plan/espaciado --


async def test_crear_plan_con_semana_inexistente_devuelve_404(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    fuerza_id = await _tipo_sesion_id(sesion, "fuerza")
    respuesta = await cliente.post(
        "/api/v1/planes",
        json={"ciclo_semana_id": 999999, "tipo_sesion_id": fuerza_id},
    )
    assert respuesta.status_code == 404


async def test_espaciado_fuerza_rechaza_menos_de_min_dias_y_acepta_en_el_limite(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """`fuerza_separacion_min_horas` = 48h -> mínimo 2 días entre sesiones de
    fuerza (REGLAS_NEGOCIO §13.3, aproximación por día dado el grano diario
    del schema)."""
    ciclo = await cliente.post(
        "/api/v1/ciclos",
        json={
            "numero": 1,
            "objetivo": "Pretemporada",
            "fecha_inicio": "2026-08-03",  # lunes
            "semanas": 4,
        },
    )
    ciclo_id = ciclo.json()["id"]
    semana = await cliente.post(
        f"/api/v1/ciclos/{ciclo_id}/semanas",
        json={"numero": 1, "fase": "carga", "volumen_pct": 100},
    )
    semana_id = semana.json()["id"]
    fuerza_id = await _tipo_sesion_id(sesion, "fuerza")

    primero = await cliente.post(
        "/api/v1/planes",
        json={
            "ciclo_semana_id": semana_id,
            "tipo_sesion_id": fuerza_id,
            "dia_sugerido": 0,
        },
    )
    assert primero.status_code == 200

    rechazado = await cliente.post(
        "/api/v1/planes",
        json={
            "ciclo_semana_id": semana_id,
            "tipo_sesion_id": fuerza_id,
            "dia_sugerido": 1,
        },
    )
    assert rechazado.status_code == 422

    aceptado = await cliente.post(
        "/api/v1/planes",
        json={
            "ciclo_semana_id": semana_id,
            "tipo_sesion_id": fuerza_id,
            "dia_sugerido": 2,
        },
    )
    assert aceptado.status_code == 200


async def test_espaciado_partido_rechaza_demanda_alta_en_ventana_previa(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """`partido_ventana_previa_horas` = 24h -> nada de demanda alta el día
    antes de un partido (REGLAS_NEGOCIO §13.3)."""
    ciclo = await cliente.post(
        "/api/v1/ciclos",
        json={
            "numero": 1,
            "objetivo": "Pretemporada",
            "fecha_inicio": "2026-08-03",
            "semanas": 4,
        },
    )
    ciclo_id = ciclo.json()["id"]
    semana = await cliente.post(
        f"/api/v1/ciclos/{ciclo_id}/semanas",
        json={"numero": 1, "fase": "carga", "volumen_pct": 100},
    )
    semana_id = semana.json()["id"]
    fuerza_id = await _tipo_sesion_id(sesion, "fuerza")
    partido_id = await _tipo_sesion_id(sesion, "partido")

    await cliente.post(
        "/api/v1/planes",
        json={
            "ciclo_semana_id": semana_id,
            "tipo_sesion_id": fuerza_id,
            "dia_sugerido": 0,
        },
    )

    rechazado = await cliente.post(
        "/api/v1/planes",
        json={
            "ciclo_semana_id": semana_id,
            "tipo_sesion_id": partido_id,
            "dia_sugerido": 1,
        },
    )
    assert rechazado.status_code == 422


async def test_listar_planes_de_fecha_resuelve_dia_sugerido_y_fecha_prevista(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """dia_sugerido=2 en la semana 1 de un ciclo que arranca el lunes
    2026-08-03 cae el 2026-08-05. fecha_prevista es un match directo, sin
    pasar por ciclo. Una fecha que no matchea ninguna de las dos no trae
    nada (el rango del ciclo no alcanza para filtrar el dia exacto)."""
    ciclo = await cliente.post(
        "/api/v1/ciclos",
        json={
            "numero": 1,
            "objetivo": "Pretemporada",
            "fecha_inicio": "2026-08-03",  # lunes
            "semanas": 4,
        },
    )
    ciclo_id = ciclo.json()["id"]
    semana = await cliente.post(
        f"/api/v1/ciclos/{ciclo_id}/semanas",
        json={"numero": 1, "fase": "carga", "volumen_pct": 100},
    )
    semana_id = semana.json()["id"]
    resistencia_id = await _tipo_sesion_id(sesion, "resistencia")
    recuperacion_id = await _tipo_sesion_id(sesion, "recuperacion")

    plan_por_dia = await cliente.post(
        "/api/v1/planes",
        json={
            "ciclo_semana_id": semana_id,
            "tipo_sesion_id": resistencia_id,
            "dia_sugerido": 2,  # 2026-08-03 + 2 dias = 2026-08-05
        },
    )
    plan_por_fecha = await cliente.post(
        "/api/v1/planes",
        json={"tipo_sesion_id": recuperacion_id, "fecha_prevista": "2026-08-07"},
    )

    del_dia = await cliente.get("/api/v1/planes", params={"fecha": "2026-08-05"})
    assert [p["id"] for p in del_dia.json()] == [plan_por_dia.json()["id"]]

    de_la_fecha = await cliente.get("/api/v1/planes", params={"fecha": "2026-08-07"})
    assert [p["id"] for p in de_la_fecha.json()] == [plan_por_fecha.json()["id"]]

    sin_planes = await cliente.get("/api/v1/planes", params={"fecha": "2026-08-06"})
    assert sin_planes.json() == []


async def test_crear_plan_con_series_objetivo(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    fuerza_id = await _tipo_sesion_id(sesion, "fuerza")
    ejercicio_id = await _ejercicio_de_tipo(sesion, fuerza_id)

    creado = await cliente.post(
        "/api/v1/planes",
        json={
            "tipo_sesion_id": fuerza_id,
            "fecha_prevista": "2026-08-10",
            "series": [
                {
                    "ejercicio_id": ejercicio_id,
                    "orden": 0,
                    "series": 4,
                    "reps_min": 6,
                    "reps_max": 8,
                    "peso_objetivo_kg": 80,
                }
            ],
        },
    )
    assert creado.status_code == 200
    assert len(creado.json()["series_planeadas"]) == 1
    assert creado.json()["series_planeadas"][0]["peso_objetivo_kg"] == "80.00"

    listado = await cliente.get("/api/v1/planes", params={"fecha": "2026-08-10"})
    assert len(listado.json()[0]["series_planeadas"]) == 1
