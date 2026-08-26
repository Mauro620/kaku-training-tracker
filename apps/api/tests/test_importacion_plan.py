"""Tests de la importación de plan semanal por JSON.

El contrato es `docs/PLAN_IMPORT.md`. El camino feliz se prueba contra
`plan-ejemplo.json` **sin copiarlo acá**: ese archivo es lo que el usuario le
pega a un LLM, así que si deja de importar, el documento quedó mintiendo y el
test tiene que enterarse.
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
from app.repositories.catalogo import ejercicio as repo_ejercicio
from app.services.entrenamiento.importacion import construir_export

RUTA_EJEMPLO = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "feature-01-plan-import"
    / "plan-ejemplo.json"
)
RUTA_DOC_REGLAS = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "feature-01-plan-import"
    / "PLAN_IMPORT.md"
)
RUTA_REGLAS_EMPAQUETADAS = (
    Path(__file__).resolve().parents[1] / "app" / "resources" / "reglas-import.md"
)
# Literal exacto de la línea de `sesion.tipo` en docs/PLAN_IMPORT.md §5. El
# recurso empaquetado reemplaza este bloque por `{{TIPOS_SESION}}`; en tiempo
# de ejecución se reinyecta desde el catálogo vivo, nunca desde este literal.
LITERAL_TIPOS_SESION = (
    "**`sesion.tipo`** — `fuerza`, `velocidad_salto`, `resistencia`,\n"
    "`balon_control`, `balon_distribucion`, `recuperacion`, `partido`,\n"
    "`activacion`."
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
        "version": 2,
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
        "0-activacion",
        "1-recuperacion",
        "2-partido",
        "3-fuerza",
        "4-balon_control",
        "5-fuerza",
        "6-recuperacion",
    }
    assert all(p.estado is EstadoSesionPlan.pendiente for p in planes)

    # Nombre y nota del plan (§2.3) y nota del bloque (§2.4) quedan guardados.
    priming = next(p for p in planes if p.clave_import == "0-activacion")
    assert priming.nombre == "Priming pre-partido"
    assert priming.nota is not None and "9pm" in priming.nota
    await sesion.refresh(priming, attribute_names=["bloques_planeados"])
    assert any(b.nota == "Submaximo, ~70%" for b in priming.bloques_planeados)


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
        "activacion": 1,
        "recuperacion": 2,
        "partido": 1,
        "fuerza": 2,
        "balon_control": 1,
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
            SesionPlan.clave_import == "0-activacion",
        )
    )
    assert plan is not None
    plan_id, objetivo_original = plan.id, plan.objetivo

    # fecha_inicio 2026-09-01 (martes) se ancla al lunes 2026-08-31, asi que
    # el día 0 de la semana 1 es ese mismo.
    creada = await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid.uuid4()),
            "idempotency_key": str(uuid.uuid4()),
            "sesion_plan_id": plan_id,
            "fecha": "2026-08-31",
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
    assert any("0-activacion" in a for a in cuerpo["advertencias"])

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


async def test_la_deteccion_difusa_reusa_el_ejercicio_del_catalogo(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """Minúsculas, sin tildes y sin paréntesis (PLAN_IMPORT.md §6.1): un LLM
    que escribe `hip thrust` o `Elevacion de talon` no duplica el catálogo."""
    payload = _payload_minimo()
    payload["sesiones"][0]["bloques"].append(
        {
            "ejercicio": "elevacion de talon (rumano)",
            "tipo_medicion": "carga",
            "series": 3,
            "reps": 15,
        }
    )
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["ejercicios_creados"] == []
    assert any("Elevación de talón" in a for a in cuerpo["advertencias"])

    # No se creó un duplicado con la escritura del JSON.
    assert (
        await sesion.scalar(
            select(Ejercicio).where(Ejercicio.nombre == "elevacion de talon (rumano)")
        )
    ) is None


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
    respuesta = await _importar(cliente, _payload_minimo(version=1))
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


async def test_la_descripcion_solo_se_usa_al_crear_el_ejercicio(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """El catalogo no se sobrescribe desde una importacion: si el ejercicio ya
    existe, su descripcion queda como estaba (PLAN_IMPORT.md §4.1)."""
    payload = _payload_minimo()
    payload["ciclo"]["numero"] = 21
    payload["sesiones"][0]["bloques"] = [
        {
            "ejercicio": "Pase largo diagonal",
            "tipo_medicion": "distancia",
            "reps": 20,
            "distancia_m": 30,
            "descripcion": "Contacto con el empeine interno.",
        },
        # Ya existe en el seed: la descripcion se ignora.
        {
            "ejercicio": "Hip thrust",
            "tipo_medicion": "carga",
            "series": 3,
            "reps": 8,
            "descripcion": "ESTO NO DEBE GUARDARSE",
        },
    ]
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["ejercicios_creados"] == ["Pase largo diagonal"]
    # Se conserva la del catálogo, pero *se avisa* (§4.1): si no, el usuario
    # cree que su descripcion quedo guardada y no es asi.
    assert any("Hip thrust" in a and "descripcion" in a for a in cuerpo["advertencias"])

    nuevo = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pase largo diagonal")
    )
    assert nuevo is not None
    assert nuevo.descripcion == "Contacto con el empeine interno."

    existente = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Hip thrust")
    )
    assert existente is not None
    assert existente.descripcion != "ESTO NO DEBE GUARDARSE"


async def test_reimportar_corrige_la_fecha_de_inicio_si_no_hay_nada_ejecutado(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """Sin historico no hay calendario que romper, y bloquearlo dejaba al
    usuario sin forma de arreglar una fecha mal puesta salvo borrar el ciclo."""
    payload = _payload_minimo()
    payload["ciclo"]["numero"] = 31
    payload["ciclo"]["fecha_inicio"] = "2026-08-17"
    primera = await _importar(cliente, payload)
    assert primera.status_code == 200

    payload["ciclo"]["fecha_inicio"] = "2026-08-24"
    segunda = await _importar(cliente, payload)
    assert segunda.status_code == 200
    assert any(
        "se movio del 2026-08-17 al 2026-08-24" in a
        for a in segunda.json()["advertencias"]
    )

    ciclo = await sesion.get(Ciclo, segunda.json()["ciclo_id"])
    assert ciclo is not None
    assert ciclo.fecha_inicio == date(2026, 8, 24)

    # El plan del dia 0 se movio con el ciclo.
    encontrados = await cliente.get("/api/v1/planes", params={"fecha": "2026-08-24"})
    assert [p["clave_import"] for p in encontrados.json()] == ["0-fuerza"]


async def test_no_mueve_el_ciclo_si_ya_hay_algo_ejecutado(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    payload = _payload_minimo()
    payload["ciclo"]["numero"] = 32
    payload["ciclo"]["fecha_inicio"] = "2026-08-17"
    primera = await _importar(cliente, payload)

    plan = await sesion.scalar(
        select(SesionPlan).where(
            SesionPlan.ciclo_semana_id == primera.json()["ciclo_semana_id"]
        )
    )
    assert plan is not None
    await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid.uuid4()),
            "idempotency_key": str(uuid.uuid4()),
            "sesion_plan_id": plan.id,
            "fecha": "2026-08-17",
            "tipo_sesion_id": plan.tipo_sesion_id,
            "duracion_min": 60,
            "rpe": 8,
            "bloques": [],
        },
    )

    payload["ciclo"]["fecha_inicio"] = "2026-08-24"
    segunda = await _importar(cliente, payload)
    assert segunda.status_code == 200
    assert any(
        "ya tiene 1 sesion(es) ejecutada(s)" in a
        for a in segunda.json()["advertencias"]
    )

    ciclo = await sesion.get(Ciclo, segunda.json()["ciclo_id"])
    assert ciclo is not None
    assert ciclo.fecha_inicio == date(2026, 8, 17)  # intacto


async def test_no_deja_achicar_las_semanas_por_debajo_de_las_que_existen(
    cliente: AsyncClient,
) -> None:
    """Achicarlas dejaria las ultimas fuera del rango del ciclo y sus planes
    invisibles: se rechaza en vez de romper en silencio."""
    payload = _payload_minimo()
    payload["ciclo"]["numero"] = 33
    payload["ciclo"]["semanas"] = 4
    payload["semana"]["numero"] = 3
    assert (await _importar(cliente, payload)).status_code == 200

    payload["semana"]["numero"] = 1
    payload["ciclo"]["semanas"] = 2
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 422
    assert "no se puede achicar" in respuesta.json()["detail"]


# ------------------------------------------------------- exports para LLM --


TIPOS_SESION_SEMBRADOS = (
    "fuerza",
    "velocidad_salto",
    "resistencia",
    "balon_control",
    "balon_distribucion",
    "recuperacion",
    "partido",
    "activacion",
)


async def test_construir_export_ejercicios_refleja_el_catalogo(
    sesion: AsyncSession,
) -> None:
    """Sale de `listar_ejercicios`, no de una lista hardcodeada (spec: "MUST
    NOT invent, filter, or hardcode entries")."""
    creado = await repo_ejercicio.crear(
        sesion,
        nombre="Zancada búlgara con mancuernas",
        tipo_medicion=TipoMedicion.carga,
        descripcion="Pie trasero elevado, bajada controlada.",
    )
    await sesion.commit()

    export = await construir_export(sesion, "ejercicios")

    assert export.recurso == "ejercicios"
    assert export.formato == "json"
    catalogo = json.loads(export.contenido)
    fila = next(e for e in catalogo if e["nombre"] == creado.nombre)
    assert fila["tipo_medicion"] == "carga"
    assert fila["descripcion"] == "Pie trasero elevado, bajada controlada."


async def test_construir_export_ejemplo_devuelve_el_recurso_empaquetado(
    sesion: AsyncSession,
) -> None:
    """`ejemplo` es el archivo empaquetado, verbatim (spec: "MUST return the
    packaged example plan resource verbatim, unmodified")."""
    export = await construir_export(sesion, "ejemplo")

    assert export.recurso == "ejemplo"
    assert export.formato == "json"
    esperado = RUTA_REGLAS_EMPAQUETADAS.parent.joinpath("plan-ejemplo.json").read_text(
        encoding="utf-8"
    )
    assert export.contenido == esperado


async def test_construir_export_reglas_inyecta_los_tipos_de_sesion_vivos(
    sesion: AsyncSession,
) -> None:
    """El bloque de tipos de sesión sale del catálogo en tiempo de request,
    nunca de un string congelado (spec: "MUST be rendered from that live
    catalog, never from a frozen string")."""
    export = await construir_export(sesion, "reglas")

    assert export.recurso == "reglas"
    assert export.formato == "markdown"
    assert "{{TIPOS_SESION}}" not in export.contenido
    for codigo in TIPOS_SESION_SEMBRADOS:
        assert f"`{codigo}`" in export.contenido


@pytest.mark.parametrize("recurso", ["ejercicios", "reglas", "ejemplo"])
async def test_export_autenticado_devuelve_200_y_contenido_no_vacio(
    cliente: AsyncClient, recurso: str
) -> None:
    respuesta = await cliente.get(f"/api/v1/planes/importar/export/{recurso}")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["recurso"] == recurso
    assert cuerpo["contenido"]


async def test_export_sin_token_devuelve_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as sin_auth:
        respuesta = await sin_auth.get("/api/v1/planes/importar/export/reglas")
    assert respuesta.status_code == 401


async def test_export_recurso_desconocido_devuelve_404(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/v1/planes/importar/export/cualquier-otra-cosa")
    assert respuesta.status_code == 404


async def test_export_path_traversal_devuelve_404(cliente: AsyncClient) -> None:
    """`recurso` solo se compara contra el allowlist, nunca se concatena a un
    path de filesystem (threat matrix: path traversal)."""
    respuesta = await cliente.get(
        "/api/v1/planes/importar/export/..%2F..%2Fetc%2Fpasswd"
    )
    assert respuesta.status_code == 404


async def test_las_rutas_existentes_de_planes_no_se_ven_afectadas(
    cliente: AsyncClient,
) -> None:
    """La ruta nueva (`GET /importar/export/{recurso}`) no debe hacer sombra
    ni ser tapada por `""`, `/importar` ni `/{plan_id}/descartar` (threat
    matrix: routing)."""
    payload = _payload_minimo()
    payload["ciclo"]["numero"] = 41

    creada = await cliente.post(
        "/api/v1/planes",
        json={
            "dia_sugerido": 2,
            "tipo_sesion_id": None,
            "objetivo": "Ruta regresion",
            "duracion_min_est": None,
            "rpe_objetivo": None,
            "bloques": [],
            "ciclo_semana_id": None,
        },
    )
    assert creada.status_code == 422, creada.text  # falta tipo_sesion_id valido

    importada = await _importar(cliente, payload)
    assert importada.status_code == 200, importada.text

    listado = await cliente.get("/api/v1/planes", params={"fecha": "2026-09-01"})
    assert listado.status_code == 200

    plan = await cliente.get("/api/v1/planes/importar/export/reglas")
    assert plan.status_code == 200

    descartado = await cliente.patch("/api/v1/planes/999999/descartar")
    assert descartado.status_code == 404


async def test_el_ejemplo_exportado_se_puede_reimportar(cliente: AsyncClient) -> None:
    """Cierre del loop end-to-end (spec "Round trip"): lo que `ejemplo`
    devuelve tiene que ser justo lo que `/planes/importar` acepta, sin
    ediciones."""
    export = await cliente.get("/api/v1/planes/importar/export/ejemplo")
    assert export.status_code == 200, export.text

    payload = json.loads(export.json()["contenido"])
    respuesta = await _importar(cliente, payload)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["sesiones_creadas"] == 7


def test_reglas_empaquetadas_coinciden_con_el_documento() -> None:
    """`reglas-import.md` (PLAN_IMPORT.md §9) es una copia verbatim del
    documento salvo el bloque de `sesion.tipo`, reemplazado por
    `{{TIPOS_SESION}}` para inyectarse en runtime desde el catálogo vivo. Si
    el documento cambia y el paquete no se actualiza, este test se entera."""
    if not RUTA_DOC_REGLAS.exists():
        pytest.skip("docs/ no está presente en este entorno (ej. imagen Docker)")
    doc = RUTA_DOC_REGLAS.read_text(encoding="utf-8")
    plantilla = RUTA_REGLAS_EMPAQUETADAS.read_text(encoding="utf-8")
    assert "{{TIPOS_SESION}}" in plantilla
    assert plantilla.replace("{{TIPOS_SESION}}", LITERAL_TIPOS_SESION) == doc
