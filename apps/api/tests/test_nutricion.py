"""Tests de integración de la rebanada de Fase 6: nutrición.

Camino feliz + los errores declarados por cada servicio (AGENTS.md §3.5).
Sin re-probar lo que ya cubren otros tests (rangos del schema, AUTH,
sesión de Postgres). `get_usuario_actual` se sobreescribe para no
re-probar JWT acá.
"""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import Usuario


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


# ----------------------------------------------------------- alimentos ----


async def test_listar_alimentos_devuelve_catalogo(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/v1/alimentos")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) >= 20  # el seed tiene 24
    # Huevo es el primer alimento sembrado y debe estar.
    nombres = {a["nombre"] for a in datos}
    assert "Huevo entero" in nombres


# -------------------------------------------------------------- recetas ----


async def test_crear_y_leer_receta(cliente: AsyncClient) -> None:
    """Crear una receta con dos ingredientes y leerla: la respuesta trae
    los items en el mismo orden en que se mandaron (servicio los ordena
    por insercion)."""
    payload = {
        "nombre": "Desayuno base",
        "momento_default": "desayuno",
        "items": [
            {"alimento_id": 1, "cantidad_g": "100"},  # Huevo entero
            {"alimento_id": 2, "cantidad_g": "150"},  # Pechuga de pollo
        ],
    }
    creada = await cliente.post("/api/v1/recetas", json=payload)
    assert creada.status_code == 201, creada.text
    cuerpo = creada.json()
    assert cuerpo["nombre"] == "Desayuno base"
    assert cuerpo["momento_default"] == "desayuno"
    assert len(cuerpo["items"]) == 2
    assert cuerpo["items"][0]["alimento_id"] == 1
    assert cuerpo["items"][0]["cantidad_g"] == "100.00"

    leida = await cliente.get(f"/api/v1/recetas/{cuerpo['id']}")
    assert leida.status_code == 200
    assert leida.json()["nombre"] == "Desayuno base"


async def test_crear_receta_con_alimento_inexistente_devuelve_404(
    cliente: AsyncClient,
) -> None:
    """El servicio valida que todos los alimento_id existan: si uno no
    existe, devuelve RecursoNoEncontradoError -> 404."""
    payload = {
        "nombre": "Receta rota",
        "items": [{"alimento_id": 9999, "cantidad_g": "100"}],
    }
    respuesta = await cliente.post("/api/v1/recetas", json=payload)
    assert respuesta.status_code == 404
    assert "alimento" in respuesta.json()["detail"].lower()


async def test_crear_receta_sin_items_devuelve_422(cliente: AsyncClient) -> None:
    """`min_length=1` en el schema: lista vacia es 422."""
    payload = {"nombre": "Receta vacia", "items": []}
    respuesta = await cliente.post("/api/v1/recetas", json=payload)
    assert respuesta.status_code == 422


async def test_actualizar_receta_reemplaza_items_completo(
    cliente: AsyncClient,
) -> None:
    """PUT reemplaza: si la receta tenia 2 items y mando 3, los 2 viejos
    desaparecen (mismo patron que Sesion.bloques)."""
    crear = await cliente.post(
        "/api/v1/recetas",
        json={
            "nombre": "Receta PUT",
            "items": [
                {"alimento_id": 1, "cantidad_g": "100"},
                {"alimento_id": 2, "cantidad_g": "150"},
            ],
        },
    )
    assert crear.status_code == 201
    receta_id = crear.json()["id"]

    actualizar = await cliente.put(
        f"/api/v1/recetas/{receta_id}",
        json={
            "nombre": "Receta PUT",
            "momento_default": "almuerzo",
            "items": [
                {"alimento_id": 3, "cantidad_g": "200"},  # Atun
            ],
        },
    )
    assert actualizar.status_code == 200
    cuerpo = actualizar.json()
    assert cuerpo["momento_default"] == "almuerzo"
    assert len(cuerpo["items"]) == 1
    assert cuerpo["items"][0]["alimento_id"] == 3


async def test_eliminar_receta(cliente: AsyncClient) -> None:
    crear = await cliente.post(
        "/api/v1/recetas",
        json={
            "nombre": "Para borrar",
            "items": [{"alimento_id": 1, "cantidad_g": "100"}],
        },
    )
    receta_id = crear.json()["id"]
    borrar = await cliente.delete(f"/api/v1/recetas/{receta_id}")
    assert borrar.status_code == 204
    # Volver a pedirla: 404 (servicio no distingue "no existe" de "no es mia").
    leer = await cliente.get(f"/api/v1/recetas/{receta_id}")
    assert leer.status_code == 404


async def test_macros_de_receta_suman_por_100g(cliente: AsyncClient) -> None:
    """El calculo es Σ (macro_por_100g * cantidad_g / 100). Para 100 g de
    huevo entero (143 kcal/100g) los macros deben coincidir con los del
    alimento casi exactamente."""
    crear = await cliente.post(
        "/api/v1/recetas",
        json={
            "nombre": "Solo huevo",
            "items": [{"alimento_id": 1, "cantidad_g": "100"}],
        },
    )
    receta_id = crear.json()["id"]
    macros = await cliente.get(f"/api/v1/recetas/{receta_id}/macros")
    assert macros.status_code == 200
    cuerpo = macros.json()
    assert cuerpo["kcal"] == "143.00"


# -------------------------------------------------------------- comidas ----


async def test_registrar_comida_con_receta(cliente: AsyncClient) -> None:
    """Comida con receta: la fila guarda receta_id y NO duplica items."""
    # Crear una receta primero.
    receta = await cliente.post(
        "/api/v1/recetas",
        json={
            "nombre": "Bowl de pollo",
            "items": [
                {"alimento_id": 2, "cantidad_g": "200"},
                {"alimento_id": 3, "cantidad_g": "100"},
            ],
        },
    )
    receta_id = receta.json()["id"]

    # Registrar comida con esa receta.
    crear = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-05",
            "momento": "almuerzo",
            "receta_id": receta_id,
            "idempotency_key": str(uuid4()),
        },
    )
    assert crear.status_code == 201, crear.text
    cuerpo = crear.json()
    assert cuerpo["receta_id"] == receta_id
    assert cuerpo["items"] == []  # no se duplican: los trae de la receta


async def test_registrar_comida_sin_receta_con_items(
    cliente: AsyncClient,
) -> None:
    crear = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-05",
            "momento": "merienda",
            "items": [{"alimento_id": 1, "cantidad_g": "100"}],
            "idempotency_key": str(uuid4()),
        },
    )
    assert crear.status_code == 201, crear.text
    cuerpo = crear.json()
    assert cuerpo["receta_id"] is None
    assert len(cuerpo["items"]) == 1


async def test_registrar_comida_con_receta_y_items_devuelve_422(
    cliente: AsyncClient,
) -> None:
    """XOR: el schema rechaza la combinacion invalida antes de tocar el
    servicio. 422 con detalle legible."""
    receta = await cliente.post(
        "/api/v1/recetas",
        json={
            "nombre": "Receta X",
            "items": [{"alimento_id": 1, "cantidad_g": "100"}],
        },
    )
    respuesta = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-05",
            "momento": "almuerzo",
            "receta_id": receta.json()["id"],
            "items": [{"alimento_id": 1, "cantidad_g": "100"}],
            "idempotency_key": str(uuid4()),
        },
    )
    assert respuesta.status_code == 422


async def test_registrar_comida_sin_receta_sin_items_devuelve_422(
    cliente: AsyncClient,
) -> None:
    """El servicio detecta este caso porque necesita leer la receta para
    la otra mitad de la validacion. Sin receta y sin items -> 422."""
    respuesta = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-05",
            "momento": "cena",
            "idempotency_key": str(uuid4()),
        },
    )
    assert respuesta.status_code == 422


async def test_idempotency_key_repetida_devuelve_misma_fila(
    cliente: AsyncClient,
) -> None:
    """El mismo POST con la misma key no crea duplicado (mismo patron que
    las 5 mutaciones de Fase 5)."""
    key = str(uuid4())
    payload = {
        "fecha": "2026-08-06",
        "momento": "desayuno",
        "items": [{"alimento_id": 1, "cantidad_g": "100"}],
        "idempotency_key": key,
    }
    ids: set[str] = set()
    for _ in range(3):
        r = await cliente.post("/api/v1/comidas", json=payload)
        assert r.status_code == 201
        ids.add(r.json()["id"])
        # Regresion: los items solo se agregan si la comida es nueva. Antes
        # del fix, cada retry volvia a insertar el mismo item suelto.
        assert len(r.json()["items"]) == 1
    assert len(ids) == 1


async def test_listar_comidas_del_dia_con_macros(cliente: AsyncClient) -> None:
    """GET /comidas?fecha=X devuelve todas las comidas + macros del dia
    en un solo viaje."""
    await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-07",
            "momento": "desayuno",
            "items": [{"alimento_id": 1, "cantidad_g": "100"}],
            "idempotency_key": str(uuid4()),
        },
    )
    await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-07",
            "momento": "almuerzo",
            "items": [{"alimento_id": 2, "cantidad_g": "150"}],
            "idempotency_key": str(uuid4()),
        },
    )
    respuesta = await cliente.get("/api/v1/comidas?fecha=2026-08-07")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["comidas"]) == 2
    # Huevo 100g (143 kcal) + Pechuga 150g (180 kcal) = 323 kcal.
    assert cuerpo["macros_del_dia"]["kcal"] == "323.00"


async def test_obtener_comida_con_macros(cliente: AsyncClient) -> None:
    crear = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-08",
            "momento": "almuerzo",
            "items": [{"alimento_id": 2, "cantidad_g": "200"}],
            "idempotency_key": str(uuid4()),
        },
    )
    comida_id = crear.json()["id"]
    respuesta = await cliente.get(f"/api/v1/comidas/{comida_id}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "macros" in cuerpo
    assert cuerpo["macros"]["kcal"] == "240.00"  # 120 kcal/100g * 2


async def test_eliminar_comida(cliente: AsyncClient) -> None:
    crear = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-08",
            "momento": "cena",
            "items": [{"alimento_id": 1, "cantidad_g": "100"}],
            "idempotency_key": str(uuid4()),
        },
    )
    comida_id = crear.json()["id"]
    borrar = await cliente.delete(f"/api/v1/comidas/{comida_id}")
    assert borrar.status_code == 204
    # Volver a pedir: 404.
    leer = await cliente.get(f"/api/v1/comidas/{comida_id}")
    assert leer.status_code == 404


# -------------------------------------------------------------- despensa ---


async def test_upsert_despensa_y_listar(cliente: AsyncClient) -> None:
    """PUT crea o reemplaza. Si el alimento no estaba en la despensa del
    usuario, se crea; si ya estaba, se actualizan los flags."""
    # Primer PUT: crear.
    crear = await cliente.put(
        "/api/v1/despensa/1",
        json={"imprescindible": True, "en_stock": True},
    )
    assert crear.status_code == 204

    # Listar: aparece con los flags correctos.
    listar = await cliente.get("/api/v1/despensa")
    assert listar.status_code == 200
    cuerpo = listar.json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["alimento_id"] == 1
    assert cuerpo[0]["alimento_nombre"] == "Huevo entero"
    assert cuerpo[0]["imprescindible"] is True
    assert cuerpo[0]["en_stock"] is True

    # Segundo PUT: actualizar (marco como sin stock).
    actualizar = await cliente.put(
        "/api/v1/despensa/1",
        json={"imprescindible": True, "en_stock": False},
    )
    assert actualizar.status_code == 204

    listar = await cliente.get("/api/v1/despensa")
    assert listar.json()[0]["en_stock"] is False


async def test_lista_de_mercado_filtra_correctamente(
    cliente: AsyncClient,
) -> None:
    """Solo `imprescindible = true AND en_stock = false` aparece en la
    lista de mercado."""
    # Huevo: imprescindible + sin stock -> debe aparecer.
    await cliente.put(
        "/api/v1/despensa/1",
        json={"imprescindible": True, "en_stock": False},
    )
    # Pechuga: imprescindible + con stock -> NO aparece (en_stock=true).
    await cliente.put(
        "/api/v1/despensa/2",
        json={"imprescindible": True, "en_stock": True},
    )
    # Atun: no imprescindible, sin stock -> NO aparece.
    await cliente.put(
        "/api/v1/despensa/3",
        json={"imprescindible": False, "en_stock": False},
    )

    lista = await cliente.get("/api/v1/despensa/lista-de-mercado")
    assert lista.status_code == 200
    cuerpo = lista.json()
    items = cuerpo["items"]
    assert len(items) == 1
    assert items[0]["alimento_id"] == 1


async def test_eliminar_de_despensa(cliente: AsyncClient) -> None:
    """DELETE quita al alimento. Si no estaba, 404 (la fila no existe)."""
    await cliente.put(
        "/api/v1/despensa/1",
        json={"imprescindible": False, "en_stock": True},
    )
    borrar = await cliente.delete("/api/v1/despensa/1")
    assert borrar.status_code == 204
    # Segunda vez: 404.
    otra_vez = await cliente.delete("/api/v1/despensa/1")
    assert otra_vez.status_code == 404


# --------------------------------------- REGRESION: macros del desayuno --


async def test_macros_desayuno_3_items_con_gramos_reales(
    cliente: AsyncClient,
) -> None:
    """REGRESION: si el usuario registra un desayuno con 80 g de Avena +
    100 g de Huevo + 120 g de Banano, los macros del dia deben reflejar
    la formula `macro = macro_por_100g * cantidad_g / 100` (REGLAS_NEGOCIO §12).

    Caso reportado: la UI mostro 8.36 kcal / 0.53 g proteina para un
    desayuno de 3 items. Eso es tres ordenes de magnitud abajo. La causa
    fue UX, no bug del calculo: el form permitia registrar "1" en vez de
    "100 g" y el server aplicaba la formula correctamente sobre 1 g.
    """
    # Precios del catalogo sembrado (kcal_100g, proteina_100g):
    #   Avena en hojuelas: 389 kcal, 16.9 g
    #   Huevo entero:      143 kcal, 12.6 g
    #   Banano:             89 kcal,  1.1 g
    # Formula: macro * g / 100
    #   Avena:    80/100  -> 311.2 kcal, 13.52 g prot
    #   Huevo:    100/100 -> 143.0 kcal, 12.60 g prot
    #   Banano:   120/100 -> 106.8 kcal,  1.32 g prot
    #   Total:              561.0 kcal, 27.44 g prot
    crear = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-09",
            "momento": "desayuno",
            "items": [
                {"alimento_id": 10, "cantidad_g": "80"},  # Avena
                {"alimento_id": 1, "cantidad_g": "100"},  # Huevo entero
                {"alimento_id": 23, "cantidad_g": "120"},  # Banano
            ],
            "idempotency_key": str(uuid4()),
        },
    )
    assert crear.status_code == 201, crear.text

    respuesta = await cliente.get("/api/v1/comidas?fecha=2026-08-09")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    macros = cuerpo["macros_del_dia"]

    # El calculo cierra a 2 decimales (ver services/nutricion/calculo.py).
    assert macros["kcal"] == "561.00"
    assert macros["proteina"] == "27.44"
    assert macros["carbo"] == "81.10"
    assert macros["grasa"] == "15.38"


async def test_macros_con_cantidad_en_gramos_enteros_no_porciones(
    cliente: AsyncClient,
) -> None:
    """Test paralelo al de arriba, pero con la causa del bug original:
    el usuario escribio "3" sin unidad y el server lo guardo como 3 g.
    La formula es correcta: 3 g de huevo = 4.29 kcal. No es un bug del
    server, es del UX del form (ver H1-H3)."""
    crear = await cliente.post(
        "/api/v1/comidas",
        json={
            "fecha": "2026-08-10",
            "momento": "desayuno",
            "items": [
                {"alimento_id": 1, "cantidad_g": "3"},  # 3 g de huevo
                {"alimento_id": 12, "cantidad_g": "1"},  # 1 g de pan
                {"alimento_id": 24, "cantidad_g": "1"},  # 1 g de aguacate
            ],
            "idempotency_key": str(uuid4()),
        },
    )
    assert crear.status_code == 201

    respuesta = await cliente.get("/api/v1/comidas?fecha=2026-08-10")
    macros = respuesta.json()["macros_del_dia"]
    # 3*143/100 + 1*247/100 + 1*160/100 = 4.29 + 2.47 + 1.60 = 8.36 kcal
    assert macros["kcal"] == "8.36"
