"""Tests de la importación de plan semanal por JSON.

El contrato es `docs/feature_1_session_plan_json/PLAN_IMPORT.md`. El camino
feliz se prueba contra `plan-ejemplo.json` **sin copiarlo acá**: ese archivo es
lo que el usuario le pega a un LLM, así que si deja de importar, el documento
quedó mintiendo y el test tiene que enterarse.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import (
    Ciclo,
    CicloSemanaComposicion,
    Ejercicio,
    SesionPlan,
    TipoSesion,
    Usuario,
)
from app.models.enums import EstadoSesionPlan, TipoMedicion

RUTA_EJEMPLO = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "feature_1_session_plan_json"
    / "plan-ejemplo.json"
)


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


def _ejemplo() -> dict[str, Any]:
    with RUTA_EJEMPLO.open(encoding="utf-8") as f:
        datos: dict[str, Any] = json.load(f)
    return datos


def _payload_minimo(**cambios: Any) -> dict[str, Any]:
    """Una semana de una sola sesión, para probar una regla por vez."""
    base: dict[str, Any] = {
        "version": 1,
        "ciclo": {
            "numero": 7,
            "objetivo": "Ciclo de prueba",
            "fecha_inicio": "2026-09-01",
            "semanas": 4,
        },
        "semana": {"numero": 1, "fase": "carga", "volumen_pct": 100},
        "sesiones": [
            {
                "dia": 0,
                "tipo": "fuerza",
                "objetivo": "Piernas",
                "duracion_min": 60,
                "rpe_objetivo": 8,
                "bloques": [
                    {
                        "ejercicio": "Hip thrust",
                        "tipo_medicion": "carga",
                        "series": 3,
                        "reps": 8,
                        "peso_kg": 100,
                    }
                ],
            }
        ],
    }
    base.update(cambios)
    return base


async def _importar(cliente: AsyncClient, payload: dict[str, Any]) -> Any:
    return await cliente.post("/api/v1/planes/importar", json=payload)


# ------------------------------------------------------------ camino feliz --


async def test_importa_el_ejemplo_del_documento(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    respuesta = await _importar(cliente, _ejemplo())
    assert respuesta.status_code == 200, respuesta.text

    cuerpo = respuesta.json()
    assert cuerpo["sesiones_creadas"] == 7
    assert cuerpo["sesiones_reemplazadas"] == 0
    assert cuerpo["sesiones_omitidas"] == 0

    planes = (
        await sesion.scalars(
            select(SesionPlan).where(
                SesionPlan.ciclo_semana_id == cuerpo["ciclo_semana_id"]
            )
        )
    ).all()
    assert len(planes) == 7
    assert {p.clave_import for p in planes} == {
        "0-fuerza",
        "1-balon_control",
        "2-velocidad_salto",
        "3-balon_distribucion",
        "4-fuerza",
        "5-resistencia",
        "6-recuperacion",
    }
    assert all(p.estado is EstadoSesionPlan.pendiente for p in planes)


async def test_la_composicion_se_deriva_de_las_sesiones(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """No se declara aparte: si el JSON trae 2 de fuerza, eso *es* la
    composición (PLAN_IMPORT.md §3)."""
    respuesta = await _importar(cliente, _ejemplo())
    semana_id = respuesta.json()["ciclo_semana_id"]

    filas = (
        await sesion.scalars(
            select(CicloSemanaComposicion).where(
                CicloSemanaComposicion.ciclo_semana_id == semana_id
            )
        )
    ).all()
    tipos = {t.id: t.codigo for t in (await sesion.scalars(select(TipoSesion))).all()}
    composicion = {tipos[f.tipo_sesion_id]: f.cantidad_objetivo for f in filas}

    assert composicion == {
        "fuerza": 2,
        "balon_control": 1,
        "velocidad_salto": 1,
        "balon_distribucion": 1,
        "resistencia": 1,
        "recuperacion": 1,
    }


async def test_reps_exacto_se_guarda_como_rango_de_amplitud_cero(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    respuesta = await _importar(cliente, _payload_minimo())
    semana_id = respuesta.json()["ciclo_semana_id"]

    plan = await sesion.scalar(
        select(SesionPlan).where(SesionPlan.ciclo_semana_id == semana_id)
    )
    assert plan is not None
    await sesion.refresh(plan, attribute_names=["bloques_planeados"])
    bloque = plan.bloques_planeados[0]
    assert (bloque.reps_min, bloque.reps_max) == (8, 8)
    assert bloque.series == 3


# --------------------------------------------------------------- idempotencia --


async def test_reimportar_reemplaza_en_vez_de_duplicar(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    primera = await _importar(cliente, _ejemplo())
    assert primera.json()["sesiones_creadas"] == 7

    segunda = await _importar(cliente, _ejemplo())
    cuerpo = segunda.json()
    assert cuerpo["sesiones_creadas"] == 0
    assert cuerpo["sesiones_reemplazadas"] == 7

    planes = (
        await sesion.scalars(
            select(SesionPlan).where(
                SesionPlan.ciclo_semana_id == cuerpo["ciclo_semana_id"]
            )
        )
    ).all()
    assert len(planes) == 7


async def test_no_reemplaza_un_plan_ya_ejecutado(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """El histórico es intocable: se omite y se reporta (PLAN_IMPORT.md §2.2)."""
    primera = await _importar(cliente, _ejemplo())
    semana_id = primera.json()["ciclo_semana_id"]

    plan = await sesion.scalar(
        select(SesionPlan).where(
            SesionPlan.ciclo_semana_id == semana_id,
            SesionPlan.clave_import == "0-fuerza",
        )
    )
    assert plan is not None
    plan_id, objetivo_original = plan.id, plan.objetivo

    # fecha_inicio 2026-09-01 (martes) se ancla al lunes 2026-08-31, asi que
    # la semana 2 arranca el 2026-09-07 y su día 0 es ese mismo.
    creada = await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid.uuid4()),
            "idempotency_key": str(uuid.uuid4()),
            "sesion_plan_id": plan_id,
            "fecha": "2026-09-07",
            "tipo_sesion_id": plan.tipo_sesion_id,
            "duracion_min": 60,
            "rpe": 8,
            "bloques": [],
        },
    )
    assert creada.status_code == 200

    await sesion.refresh(plan, attribute_names=["estado"])
    assert plan.estado is EstadoSesionPlan.cumplido

    segunda = await _importar(cliente, _ejemplo())
    cuerpo = segunda.json()
    assert cuerpo["sesiones_omitidas"] == 1
    assert cuerpo["sesiones_reemplazadas"] == 6
    assert any("0-fuerza" in a for a in cuerpo["advertencias"])

    sobreviviente = await sesion.get(SesionPlan, plan_id)
    assert sobreviviente is not None
    assert sobreviviente.objetivo == objetivo_original


# ----------------------------------------------------------------- estado --


async def test_una_sesion_en_otro_dia_deja_el_plan_en_movido(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    respuesta = await _importar(cliente, _payload_minimo())
    plan = await sesion.scalar(
        select(SesionPlan).where(
            SesionPlan.ciclo_semana_id == respuesta.json()["ciclo_semana_id"]
        )
    )
    assert plan is not None

    # dia 0 de la semana 1 es 2026-08-31 (lunes); se entrena el 2026-09-02.
    creada = await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid.uuid4()),
            "idempotency_key": str(uuid.uuid4()),
            "sesion_plan_id": plan.id,
            "fecha": "2026-09-02",
            "tipo_sesion_id": plan.tipo_sesion_id,
            "duracion_min": 60,
            "rpe": 8,
            "bloques": [],
        },
    )
    assert creada.status_code == 200
    await sesion.refresh(plan, attribute_names=["estado"])
    assert plan.estado is EstadoSesionPlan.movido


async def test_borrar_la_sesion_devuelve_el_plan_a_pendiente(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    respuesta = await _importar(cliente, _payload_minimo())
    plan = await sesion.scalar(
        select(SesionPlan).where(
            SesionPlan.ciclo_semana_id == respuesta.json()["ciclo_semana_id"]
        )
    )
    assert plan is not None

    sesion_id = str(uuid.uuid4())
    await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": sesion_id,
            "idempotency_key": str(uuid.uuid4()),
            "sesion_plan_id": plan.id,
            "fecha": "2026-08-31",
            "tipo_sesion_id": plan.tipo_sesion_id,
            "duracion_min": 60,
            "rpe": 8,
            "bloques": [],
        },
    )
    await sesion.refresh(plan, attribute_names=["estado"])
    assert plan.estado is EstadoSesionPlan.cumplido

    borrada = await cliente.delete(f"/api/v1/sesiones/{sesion_id}")
    assert borrada.status_code in (200, 204)
    await sesion.refresh(plan, attribute_names=["estado"])
    assert plan.estado is EstadoSesionPlan.pendiente


async def test_descartar_un_plan_y_no_poder_descartar_uno_ejecutado(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    respuesta = await _importar(cliente, _payload_minimo())
    plan = await sesion.scalar(
        select(SesionPlan).where(
            SesionPlan.ciclo_semana_id == respuesta.json()["ciclo_semana_id"]
        )
    )
    assert plan is not None

    descartado = await cliente.patch(f"/api/v1/planes/{plan.id}/descartar")
    assert descartado.status_code == 200
    assert descartado.json()["estado"] == "descartado"

    await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid.uuid4()),
            "idempotency_key": str(uuid.uuid4()),
            "sesion_plan_id": plan.id,
            "fecha": "2026-08-31",
            "tipo_sesion_id": plan.tipo_sesion_id,
            "duracion_min": 60,
            "rpe": 8,
            "bloques": [],
        },
    )
    # Ejecutar gana sobre descartar: el entrenamiento pasó de verdad.
    await sesion.refresh(plan, attribute_names=["estado"])
    assert plan.estado is EstadoSesionPlan.cumplido

    de_nuevo = await cliente.patch(f"/api/v1/planes/{plan.id}/descartar")
    assert de_nuevo.status_code == 422


# --------------------------------------------------------------- catálogo --


async def test_crea_los_ejercicios_que_no_existen_y_los_reporta(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    payload = _payload_minimo()
    payload["sesiones"][0]["bloques"].append(
        {
            "ejercicio": "Pase largo diagonal",
            "tipo_medicion": "distancia",
            "reps": 20,
            "distancia_m": 30,
        }
    )
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 200
    assert respuesta.json()["ejercicios_creados"] == ["Pase largo diagonal"]

    creado = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pase largo diagonal")
    )
    assert creado is not None
    assert creado.tipo_medicion is TipoMedicion.distancia


async def test_rechaza_cambiar_el_tipo_medicion_de_un_ejercicio_existente(
    cliente: AsyncClient,
) -> None:
    """Cambiarlo invalidaría los bloques históricos medidos con el anterior."""
    payload = _payload_minimo()
    payload["sesiones"][0]["bloques"] = [
        {"ejercicio": "Hip thrust", "tipo_medicion": "tiempo", "duracion_s": 90}
    ]
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 422
    assert "tipo_medicion" in respuesta.json()["detail"]


# ------------------------------------------------------------- validación --


async def test_rechaza_un_tipo_de_sesion_que_no_esta_en_el_catalogo(
    cliente: AsyncClient,
) -> None:
    payload = _payload_minimo()
    payload["sesiones"][0]["tipo"] = "yoga_lunar"
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 422
    assert "yoga_lunar" in respuesta.json()["detail"]


async def test_rechaza_un_campo_que_no_corresponde_al_tipo_medicion(
    cliente: AsyncClient,
) -> None:
    payload = _payload_minimo()
    payload["sesiones"][0]["bloques"] = [
        {
            "ejercicio": "Fartlek",
            "tipo_medicion": "tiempo",
            "duracion_s": 900,
            "peso_kg": 20,
        }
    ]
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 422
    assert "peso" in respuesta.json()["detail"]


async def test_rechaza_una_semana_que_excede_el_ciclo(cliente: AsyncClient) -> None:
    payload = _payload_minimo()
    payload["semana"]["numero"] = 9
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 422


async def test_rechaza_dos_sesiones_con_el_mismo_dia_y_tipo(
    cliente: AsyncClient,
) -> None:
    payload = _payload_minimo()
    payload["sesiones"].append(dict(payload["sesiones"][0]))
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 422


async def test_rechaza_una_version_no_soportada(cliente: AsyncClient) -> None:
    respuesta = await _importar(cliente, _payload_minimo(version=2))
    assert respuesta.status_code == 422


async def test_rechaza_reps_junto_con_reps_min_y_max(cliente: AsyncClient) -> None:
    payload = _payload_minimo()
    payload["sesiones"][0]["bloques"][0].update(
        {"reps": 8, "reps_min": 6, "reps_max": 10}
    )
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 422


# ------------------------------------------------------------ advertencias --


async def test_advierte_dos_fuerzas_a_menos_de_48_horas_sin_bloquear(
    cliente: AsyncClient,
) -> None:
    payload = _payload_minimo()
    segunda = json.loads(json.dumps(payload["sesiones"][0]))
    segunda["dia"] = 1
    payload["sesiones"].append(segunda)

    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["sesiones_creadas"] == 2
    avisos_fuerza = [a for a in cuerpo["advertencias"] if "fuerza" in a]
    # Una sola vez, no una por cada lado del conflicto.
    assert len(avisos_fuerza) == 1


async def test_el_ciclo_se_ancla_al_lunes_de_su_semana(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """`dia_sugerido` 0=lunes solo es cierto si fecha_inicio cae lunes: el
    rango de la semana se deriva de ella (REGLAS_NEGOCIO §13.3)."""
    payload = _payload_minimo()
    payload["ciclo"]["numero"] = 11
    payload["ciclo"]["fecha_inicio"] = "2026-08-23"  # domingo

    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 200

    ciclo = await sesion.get(Ciclo, respuesta.json()["ciclo_id"])
    assert ciclo is not None
    assert ciclo.fecha_inicio == date(2026, 8, 17)  # lunes anterior
    assert ciclo.fecha_inicio.weekday() == 0


async def test_el_plan_del_dia_0_cae_lunes(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """Cierre del bucle: con el anclaje, el plan de `dia: 0` se resuelve el
    lunes de esa semana y no un día antes."""
    payload = _payload_minimo()
    payload["ciclo"]["numero"] = 12
    payload["ciclo"]["fecha_inicio"] = "2026-08-23"  # domingo
    await _importar(cliente, payload)

    encontrados = await cliente.get("/api/v1/planes", params={"fecha": "2026-08-17"})
    assert encontrados.status_code == 200
    assert [p["clave_import"] for p in encontrados.json()] == ["0-fuerza"]

    vacio = await cliente.get("/api/v1/planes", params={"fecha": "2026-08-16"})
    assert vacio.json() == []
