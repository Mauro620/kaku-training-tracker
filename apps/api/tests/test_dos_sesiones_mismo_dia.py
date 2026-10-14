"""Dos sesiones planeadas el mismo dia (ej. activacion + partido) y recuperar un
plan descartado por error (PATCH /planes/{id}/recuperar).

Contexto: la pantalla Entreno asumia una sola sesion por dia y, al registrar
la primera, no dejaba iniciar la segunda. El backend nunca lo impidio; estos
tests lo fijan para que no empiece a hacerlo.
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
from app.models import TipoSesion, Usuario

LUNES = "2026-10-19"
MIERCOLES = "2026-10-21"  # dia 2 de la semana 1


@pytest.fixture
async def cliente(sesion: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    usuario = await sesion.scalar(select(Usuario))

    async def _sesion_de_prueba() -> AsyncGenerator[AsyncSession, None]:
        yield sesion

    app.dependency_overrides[get_session] = _sesion_de_prueba
    app.dependency_overrides[get_usuario_actual] = lambda: usuario
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


async def _tipo(sesion: AsyncSession, codigo: str) -> int:
    t = await sesion.scalar(select(TipoSesion.id).where(TipoSesion.codigo == codigo))
    assert t is not None
    return t


async def _importar_dos_planes_el_miercoles(cliente: AsyncClient) -> dict[str, int]:
    r = await cliente.post(
        "/api/v1/planes/importar",
        json={
            "version": 2,
            "ciclo": {"numero": 1, "objetivo": "Prueba", "fecha_inicio": LUNES},
            "semana": {"numero": 1, "fase": "carga"},
            "sesiones": [
                {"dia": 2, "tipo": "activacion", "duracion_min": 20},
                {"dia": 2, "tipo": "partido", "duracion_min": 90},
            ],
        },
    )
    assert r.status_code == 200, r.text
    planes = (await cliente.get(f"/api/v1/planes?fecha={MIERCOLES}")).json()
    return {p["tipo_sesion_id"]: p["id"] for p in planes}


async def _registrar(
    cliente: AsyncClient, plan_id: int, tipo_sesion_id: int, minutos: int
) -> dict:  # type: ignore[type-arg]
    r = await cliente.post(
        "/api/v1/sesiones",
        json={
            "id": str(uuid.uuid4()),
            "idempotency_key": str(uuid.uuid4()),
            "sesion_plan_id": plan_id,
            "fecha": MIERCOLES,
            "tipo_sesion_id": tipo_sesion_id,
            "duracion_min": minutos,
            "rpe": 3,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


async def _estados(cliente: AsyncClient) -> dict[int, str]:
    planes = (await cliente.get(f"/api/v1/planes?fecha={MIERCOLES}")).json()
    return {p["tipo_sesion_id"]: p["estado"] for p in planes}


async def test_se_pueden_registrar_las_dos_sesiones_del_mismo_dia(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    activacion, partido = (
        await _tipo(sesion, "activacion"),
        await _tipo(sesion, "partido"),
    )
    planes = await _importar_dos_planes_el_miercoles(cliente)
    assert set(planes) == {activacion, partido}

    await _registrar(cliente, planes[activacion], activacion, 20)
    # La segunda NO queda bloqueada por la primera.
    await _registrar(cliente, planes[partido], partido, 90)

    assert await _estados(cliente) == {activacion: "cumplido", partido: "cumplido"}
    sesiones = (await cliente.get(f"/api/v1/sesiones?fecha={MIERCOLES}")).json()
    assert len(sesiones) == 2


async def test_con_la_primera_descartada_la_segunda_se_registra(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    activacion, partido = (
        await _tipo(sesion, "activacion"),
        await _tipo(sesion, "partido"),
    )
    planes = await _importar_dos_planes_el_miercoles(cliente)

    descartada = await cliente.patch(f"/api/v1/planes/{planes[activacion]}/descartar")
    assert descartada.status_code == 200
    await _registrar(cliente, planes[partido], partido, 90)

    # La descartada sigue descartada (no se la pisa por no tener sesion) y la
    # segunda quedo cumplida.
    assert await _estados(cliente) == {activacion: "descartado", partido: "cumplido"}


async def test_un_plan_ya_ejecutado_no_se_puede_descartar(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    activacion = await _tipo(sesion, "activacion")
    planes = await _importar_dos_planes_el_miercoles(cliente)
    await _registrar(cliente, planes[activacion], activacion, 20)

    r = await cliente.patch(f"/api/v1/planes/{planes[activacion]}/descartar")
    assert r.status_code == 422


# ------------------------------------------------ recuperar un descarte --


async def test_un_plan_descartado_vuelve_a_pendiente(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    partido = await _tipo(sesion, "partido")
    planes = await _importar_dos_planes_el_miercoles(cliente)
    await cliente.patch(f"/api/v1/planes/{planes[partido]}/descartar")
    assert (await _estados(cliente))[partido] == "descartado"

    r = await cliente.patch(f"/api/v1/planes/{planes[partido]}/recuperar")

    assert r.status_code == 200
    assert r.json()["estado"] == "pendiente"
    assert (await _estados(cliente))[partido] == "pendiente"


async def test_un_plan_recuperado_se_puede_ejecutar(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    partido = await _tipo(sesion, "partido")
    planes = await _importar_dos_planes_el_miercoles(cliente)
    await cliente.patch(f"/api/v1/planes/{planes[partido]}/descartar")
    await cliente.patch(f"/api/v1/planes/{planes[partido]}/recuperar")

    await _registrar(cliente, planes[partido], partido, 90)

    assert (await _estados(cliente))[partido] == "cumplido"


async def test_recuperar_no_toca_los_demas_planes(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    activacion = await _tipo(sesion, "activacion")
    partido = await _tipo(sesion, "partido")
    planes = await _importar_dos_planes_el_miercoles(cliente)
    await cliente.patch(f"/api/v1/planes/{planes[activacion]}/descartar")
    await cliente.patch(f"/api/v1/planes/{planes[partido]}/descartar")

    await cliente.patch(f"/api/v1/planes/{planes[partido]}/recuperar")

    assert await _estados(cliente) == {activacion: "descartado", partido: "pendiente"}


async def test_solo_se_recupera_un_plan_descartado(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    activacion = await _tipo(sesion, "activacion")
    partido = await _tipo(sesion, "partido")
    planes = await _importar_dos_planes_el_miercoles(cliente)
    await _registrar(cliente, planes[activacion], activacion, 20)

    # pendiente: nada que recuperar
    pendiente = await cliente.patch(f"/api/v1/planes/{planes[partido]}/recuperar")
    assert pendiente.status_code == 422
    # cumplido: lo resuelve el sistema, no se toca a mano
    cumplido = await cliente.patch(f"/api/v1/planes/{planes[activacion]}/recuperar")
    assert cumplido.status_code == 422
    assert (await _estados(cliente))[activacion] == "cumplido"


async def test_recuperar_un_plan_inexistente_es_404(cliente: AsyncClient) -> None:
    assert (await cliente.patch("/api/v1/planes/999999/recuperar")).status_code == 404
