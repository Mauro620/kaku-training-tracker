"""Perfil del atleta (Cambio 2): seed, GET/PUT y validaciones.

`get_usuario_actual` se sobreescribe para no re-probar JWT acá.
"""

from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import PerfilAtleta, Usuario
from app.seeds.__main__ import sembrar
from tests.conftest import NOMBRE_USUARIO_SEED


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


def _perfil_valido() -> dict[str, Any]:
    return {
        "posicion": "Mediocampista",
        "rol_tactico": "Box to box",
        "pie_dominante": "izquierdo",
        "talla_cm": "180.0",
        "peso_kg": "75.50",
        "lesiones_activas": ["Esguince de tobillo"],
        "objetivos": ["Uno", "Dos"],
        "eventos_fijos": [
            {"dia": 1, "hora": "20:30", "tipo_sesion": "partido", "nombre": "Liga"}
        ],
        "ventanas": [
            {"dia": 0, "inicio": "08:00", "fin": "09:00", "lugares": ["Gimnasio"]}
        ],
        "lugares": [{"nombre": "Gimnasio", "equipamiento": ["barra", "mancuernas"]}],
        "equipamiento_propio": ["balón"],
    }


async def test_el_seed_crea_el_perfil_con_los_datos_del_atleta(
    cliente: AsyncClient,
) -> None:
    r = await cliente.get("/api/v1/perfil")
    assert r.status_code == 200
    perfil = r.json()
    assert perfil["posicion"] == "Extremo izquierdo"
    assert perfil["lesiones_activas"] == []
    assert float(perfil["talla_cm"]) == 178.0
    assert float(perfil["peso_kg"]) == 80.0
    assert len(perfil["objetivos"]) == 5
    assert "12 %" in perfil["objetivos"][4]
    # Lo que lleva consigo, aparte del equipamiento de cada lugar.
    assert perfil["equipamiento_propio"] == [
        "conos",
        "balón",
        "bandas de resistencia",
        "paralelas",
    ]
    gimnasio = next(x for x in perfil["lugares"] if x["nombre"] == "Gimnasio")
    assert gimnasio["equipamiento"] == ["gimnasio completo"]
    assert perfil["objetivos"][0].startswith("Retomar regularidad")
    assert [
        (e["dia"], e["hora"], e["tipo_sesion"]) for e in perfil["eventos_fijos"]
    ] == [
        (0, "21:00", "partido"),
        (2, "21:00", "partido"),
    ]
    # Domingo (6) es descanso: sin ventana. Lunes a sabado tienen una.
    assert sorted(v["dia"] for v in perfil["ventanas"]) == [0, 1, 2, 3, 4, 5]
    nombres = {lugar["nombre"] for lugar in perfil["lugares"]}
    assert all(set(v["lugares"]) <= nombres for v in perfil["ventanas"])


async def test_resembrar_no_pisa_los_cambios_del_usuario(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    r = await cliente.put("/api/v1/perfil", json=_perfil_valido())
    assert r.status_code == 200
    await sembrar(sesion, NOMBRE_USUARIO_SEED)
    perfil = await sesion.scalar(select(PerfilAtleta))
    assert perfil is not None
    assert perfil.posicion == "Mediocampista"


async def test_put_reemplaza_el_perfil_completo(cliente: AsyncClient) -> None:
    r = await cliente.put("/api/v1/perfil", json=_perfil_valido())
    assert r.status_code == 200
    guardado = (await cliente.get("/api/v1/perfil")).json()
    assert guardado["posicion"] == "Mediocampista"
    assert guardado["objetivos"] == ["Uno", "Dos"]
    assert guardado["lugares"][0]["equipamiento"] == ["barra", "mancuernas"]
    assert guardado["ventanas"][0]["inicio"] == "08:00"
    assert guardado["equipamiento_propio"] == ["balón"]
    assert len(guardado["eventos_fijos"]) == 1


async def test_put_acepta_lesiones_y_listas_vacias(cliente: AsyncClient) -> None:
    cuerpo = _perfil_valido() | {
        "lesiones_activas": [],
        "objetivos": [],
        "eventos_fijos": [],
        "ventanas": [],
        "lugares": [],
        "equipamiento_propio": [],
    }
    r = await cliente.put("/api/v1/perfil", json=cuerpo)
    assert r.status_code == 200
    assert r.json()["ventanas"] == []


async def test_get_sin_perfil_devuelve_404(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    perfil = await sesion.scalar(select(PerfilAtleta))
    assert perfil is not None
    await sesion.delete(perfil)
    await sesion.flush()
    assert (await cliente.get("/api/v1/perfil")).status_code == 404


async def test_put_rechaza_tipo_de_sesion_desconocido(cliente: AsyncClient) -> None:
    cuerpo = _perfil_valido()
    cuerpo["eventos_fijos"][0]["tipo_sesion"] = "yoga"
    r = await cliente.put("/api/v1/perfil", json=cuerpo)
    assert r.status_code == 422
    assert "yoga" in r.json()["detail"]


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("dia", 7),
        ("hora", "25:00"),
        ("hora", "9:00"),
    ],
)
async def test_put_rechaza_evento_fijo_invalido(
    cliente: AsyncClient, campo: str, valor: Any
) -> None:
    cuerpo = _perfil_valido()
    cuerpo["eventos_fijos"][0][campo] = valor
    assert (await cliente.put("/api/v1/perfil", json=cuerpo)).status_code == 422


async def test_put_rechaza_ventana_con_inicio_posterior_al_fin(
    cliente: AsyncClient,
) -> None:
    cuerpo = _perfil_valido()
    cuerpo["ventanas"][0].update(inicio="10:00", fin="09:00")
    assert (await cliente.put("/api/v1/perfil", json=cuerpo)).status_code == 422


async def test_put_rechaza_ventana_con_lugar_no_declarado(
    cliente: AsyncClient,
) -> None:
    cuerpo = _perfil_valido()
    cuerpo["ventanas"][0]["lugares"] = ["Piscina"]
    r = await cliente.put("/api/v1/perfil", json=cuerpo)
    assert r.status_code == 422
    assert "Piscina" in r.text


async def test_put_rechaza_lugares_repetidos_y_campos_desconocidos(
    cliente: AsyncClient,
) -> None:
    cuerpo = _perfil_valido()
    cuerpo["lugares"].append({"nombre": "Gimnasio", "equipamiento": []})
    assert (await cliente.put("/api/v1/perfil", json=cuerpo)).status_code == 422
    assert (
        await cliente.put("/api/v1/perfil", json=_perfil_valido() | {"extra": 1})
    ).status_code == 422


async def test_el_seed_fija_el_peso_objetivo_y_no_lo_pisa(
    sesion: AsyncSession,
) -> None:
    usuario = await sesion.scalar(select(Usuario))
    assert usuario is not None
    assert usuario.peso_objetivo_kg == Decimal("75.00")

    # Si el usuario lo cambia, volver a sembrar lo respeta.
    usuario.peso_objetivo_kg = Decimal("76.50")
    await sesion.flush()
    await sembrar(sesion, NOMBRE_USUARIO_SEED)
    await sesion.refresh(usuario)
    assert usuario.peso_objetivo_kg == Decimal("76.50")
