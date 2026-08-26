"""Tests del banco de ejercicios (PR 2 del feature 2).

Cubre R6 (catalog CRUD): schemas extendidos, repositorio `listar_filtrado`,
repositorio `obtener_detalle`, service `listar_ejercicios_filtrado`,
service `obtener_detalle_ejercicio`, y los endpoints extendidos
(POST/PATCH con campos nuevos, GET /{id}).

Los tests de schema van primero: no tocan la base, solo verifican que el
contrato de Pydantic coincide con lo que dice el design #326. Sin ellos,
los tests de integracion no podrian confiar en que el router acepta/rechaza
lo que corresponde.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import Ejercicio, TipoSesion, Usuario
from app.models.enums import TipoMedicion
from app.repositories.catalogo import ejercicio as repo_ejercicio
from app.repositories.entrenamiento import bloque as repo_bloque
from app.repositories.entrenamiento import sesion as repo_sesion
from app.schemas.catalogo.catalogo import (
    EjercicioCreate,
    EjercicioDetalleRead,
    EjercicioHistorialItem,
    EjercicioListItem,
    EjercicioListRead,
    EjercicioPosibleDuplicado,
    EjercicioRead,
    EjercicioUpdate,
)


@pytest.fixture
async def cliente(sesion: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP contra `app` con la sesion de pytest y el usuario seed."""
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


async def _ids_base(sesion: AsyncSession) -> tuple[uuid.UUID, int]:
    usuario_id = await sesion.scalar(select(Usuario.id))
    tipo_sesion_id = await sesion.scalar(
        select(TipoSesion.id).where(TipoSesion.codigo == "fuerza")
    )
    assert usuario_id is not None and tipo_sesion_id is not None
    return usuario_id, tipo_sesion_id


async def _crear_sesion_con_bloques(
    sesion: AsyncSession,
    usuario_id: uuid.UUID,
    tipo_sesion_id: int,
    ejercicio_id: int,
    *,
    fecha: date,
    cantidad_bloques: int = 1,
    serie: int = 1,
    peso_kg: Decimal | None = Decimal("80.0"),
    duracion_min: int = 60,
    rpe: int = 8,
) -> uuid.UUID:
    """Crea una sesion con N bloques del ejercicio. Usado para darle
    historial/uso al ejercicio en los tests."""
    sesion_db = await repo_sesion.crear(
        sesion,
        sesion_id=uuid.uuid4(),
        idempotency_key=uuid.uuid4(),
        usuario_id=usuario_id,
        sesion_plan_id=None,
        fecha=fecha,
        tipo_sesion_id=tipo_sesion_id,
        duracion_min=duracion_min,
        rpe=rpe,
        nota=None,
    )
    for i in range(cantidad_bloques):
        await repo_bloque.crear(
            sesion,
            sesion_id=sesion_db.id,
            ejercicio_id=ejercicio_id,
            orden=serie + i,
            series=3,
            reps=8,
            distancia_m=None,
            duracion_s=None,
            calidad=None,
            peso_kg=peso_kg,
            rpe=None,
            dolor_lumbar=False,
        )
    return sesion_db.id


# ----------------------------------------------------- schemas R6.1 ----


def test_schema_ejercicio_list_item_acepta_campos_minimos() -> None:
    """El schema de item del listado tiene los 10 campos que el frontend
    necesita para pintar la fila (id, nombre, patron, carga_lumbar,
    tipo_sesion_id, tipo_medicion, descripcion, activo, usos, ultima_vez)."""
    item = EjercicioListItem(
        id=1,
        nombre="Hip thrust",
        patron="cadera_dominante",
        carga_lumbar="media",
        tipo_sesion_id=1,
        tipo_medicion="carga",
        descripcion=None,
        activo=True,
        usos=3,
        ultima_vez=date(2026, 8, 20),
    )
    assert item.id == 1
    assert item.nombre == "Hip thrust"
    assert item.patron == "cadera_dominante"
    assert item.carga_lumbar == "media"
    assert item.tipo_sesion_id == 1
    assert item.tipo_medicion == "carga"
    assert item.descripcion is None
    assert item.activo is True
    assert item.usos == 3
    assert item.ultima_vez == date(2026, 8, 20)


def test_schema_ejercicio_list_read_items_total() -> None:
    """El envelope del listado siempre tiene `items` y `total`, en ese orden
    (lo espera el frontend y el OpenAPI generado)."""
    items = [
        EjercicioListItem(
            id=1,
            nombre="A",
            patron=None,
            carga_lumbar="baja",
            tipo_sesion_id=None,
            tipo_medicion="carga",
            descripcion=None,
            activo=True,
            usos=0,
            ultima_vez=None,
        ),
    ]
    envelope = EjercicioListRead(items=items, total=1)
    assert envelope.items == items
    assert envelope.total == 1


def test_schema_ejercicio_detalle_incluye_historial_y_duplicados() -> None:
    """El detalle expone los ultimos 5 usos (subquery) y los candidatos a
    duplicado (mismo tipo_medicion, similitud >= 0.75)."""
    historial = [
        EjercicioHistorialItem(
            sesion_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            fecha=date(2026, 8, 20),
            bloque_id=10,
            orden=1,
            series=4,
            reps=8,
            peso_kg=Decimal("80.0"),
        ),
    ]
    duplicados = [
        EjercicioPosibleDuplicado(id=2, nombre="Hip Trust", similitud=0.82),
    ]
    detalle = EjercicioDetalleRead(
        id=1,
        nombre="Hip thrust",
        patron="cadera_dominante",
        carga_lumbar="media",
        tipo_sesion_id=1,
        tipo_medicion="carga",
        descripcion="Cadera al techo.",
        activo=True,
        historial=historial,
        posibles_duplicados=duplicados,
    )
    assert detalle.id == 1
    assert detalle.historial == historial
    assert detalle.posibles_duplicados == duplicados


def test_schema_ejercicio_update_rechaza_tipo_medicion() -> None:
    """REGLAS_NEGOCIO §15: cambiar `tipo_medicion` invalidaria los bloques
    historicos. El schema tiene `extra=forbid`, asi que un cliente que mande
    `{"tipo_medicion": "carga"}` recibe 422 antes de tocar la base."""
    with pytest.raises(ValidationError) as exc:
        EjercicioUpdate(nombre="Nuevo", tipo_medicion="carga")  # type: ignore[call-arg]
    # El error menciona el campo rechazado.
    assert any("tipo_medicion" in str(err) for err in exc.value.errors())


def test_schema_ejercicio_update_descripcion_vacia_se_traduce_a_null() -> None:
    """El contrato del design: `descripcion=""` se traduce a None en el
    service. El schema acepta ambos (`None` o string vacio), y la traduccion
    ocurre en el service para no contaminar la API publica del schema."""
    # Caso 1: el usuario manda descripcion vacia.
    caso_vacio = EjercicioUpdate(descripcion="")
    assert caso_vacio.descripcion == ""

    # Caso 2: el usuario no manda descripcion (no tocar).
    caso_omitido = EjercicioUpdate()
    assert caso_omitido.descripcion is None

    # El caso 3 (traduccion a None) vive en el service; lo cubre el test
    # `test_patch_ejercicio_descripcion_vacia_pone_null` mas abajo.


# ------------------------------------------------ EjercicioCreate R6.5 ---


def test_schema_ejercicio_create_acepta_patron_y_carga_lumbar() -> None:
    """Campos nuevos respecto al legacy: patron y carga_lumbar son opcionales
    (defaults None y 'baja' respectivamente). tipo_medicion sigue siendo
    obligatorio: sin el, no se sabe que campos aceptaran los bloques."""
    ejercicio = EjercicioCreate(
        nombre="Pallof press",
        tipo_medicion="carga",
        patron="core_antirotacion",
        carga_lumbar="baja",
    )
    assert ejercicio.nombre == "Pallof press"
    assert ejercicio.tipo_medicion == "carga"
    assert ejercicio.patron == "core_antirotacion"
    assert ejercicio.carga_lumbar == "baja"


def test_schema_ejercicio_read_incluye_activo() -> None:
    """Backward-compat: el `EjercicioRead` legacy ahora expone `activo` para
    reflejar la columna nueva. Otros lugares del proyecto lo siguen
    importando (importador, tests previos)."""
    lectura = EjercicioRead(
        id=1,
        nombre="Hip thrust",
        patron="cadera_dominante",
        carga_lumbar="media",
        tipo_sesion_id=1,
        tipo_medicion="carga",
        descripcion=None,
        activo=True,
    )
    assert lectura.activo is True


# ------------------------------------------------ repositorio R6.2 (Q1) --


async def test_listar_filtrado_devuelve_los_sembrados(sesion: AsyncSession) -> None:
    """El seed tiene 29 ejercicios. Con `activo=true` (default) los lista
    todos en `items`, y `total` refleja la cantidad total sin paginar."""
    items, total = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    ejercicios = [fila[0] for fila in items]
    nombres = [e.nombre for e in ejercicios]
    assert total == 29
    assert len(items) == 29
    assert "Hip thrust" in nombres
    assert "Elevación de talón" in nombres


async def test_listar_filtrado_q_ya_normalizado_matchea(sesion: AsyncSession) -> None:
    """El repo recibe el `q` ya normalizado desde el service. La
    normalizacion de acentos vive en el service (no en Postgres, que no
    trae `unaccent` instalado). El test que verifica que `q='elevacion'` y
    `q='elevación'` producen lo mismo vive en el service."""
    items, total = await repo_ejercicio.listar_filtrado(
        sesion,
        q="elevacion",
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    assert total == 1
    assert len(items) == 1
    assert items[0][0].nombre == "Elevación de talón"


async def test_listar_filtrado_por_tipo_medicion(sesion: AsyncSession) -> None:
    """Filtra exactamente los ejercicios del `tipo_medicion` pedido."""
    items_carga, total_carga = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=TipoMedicion.carga,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    assert total_carga > 0
    assert all(fila[0].tipo_medicion is TipoMedicion.carga for fila in items_carga)

    items_tecnica, _total_tecnica = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=TipoMedicion.tecnica,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    assert all(fila[0].tipo_medicion is TipoMedicion.tecnica for fila in items_tecnica)
    # Sin solapamiento entre tipos disjuntos.
    nombres_carga = {fila[0].nombre for fila in items_carga}
    nombres_tecnica = {fila[0].nombre for fila in items_tecnica}
    assert nombres_carga.isdisjoint(nombres_tecnica)


async def test_listar_filtrado_default_excluye_archivados(
    sesion: AsyncSession,
) -> None:
    """`activo=true` (default) NO lista los archivados. `activo=false` los
    lista y oculta los activos."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    pallof.activo = False
    await sesion.flush()

    items_default, _ = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    assert all(fila[0].nombre != "Pallof press" for fila in items_default)

    items_archivados, total_archivados = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=False,
        orden="nombre",
    )
    nombres_archivados = [fila[0].nombre for fila in items_archivados]
    assert "Pallof press" in nombres_archivados
    assert total_archivados == 1


async def test_listar_filtrado_incluye_usos_y_ultima_vez(
    sesion: AsyncSession,
) -> None:
    """La query agrega `usos` (count de filas de `bloque`) y `ultima_vez`
    (max(sesion.fecha)). Sin uso: 0 y None. Con 2 sesiones: 2 usos y la
    ultima fecha."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    usuario_id, tipo_sesion_id = await _ids_base(sesion)

    # Sin uso previo.
    items_sin, _ = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    pallof_fila_sin = next(f for f in items_sin if f[0].nombre == "Pallof press")
    _, usos_sin, ultima_sin = pallof_fila_sin
    assert usos_sin == 0
    assert ultima_sin is None

    # Con dos sesiones: 1+2 = 3 bloques, ultima = fecha mas reciente.
    await _crear_sesion_con_bloques(
        sesion, usuario_id, tipo_sesion_id, pallof.id, fecha=date(2026, 8, 10)
    )
    await _crear_sesion_con_bloques(
        sesion,
        usuario_id,
        tipo_sesion_id,
        pallof.id,
        fecha=date(2026, 8, 18),
        cantidad_bloques=2,
    )
    items_con, _ = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    pallof_fila_con = next(f for f in items_con if f[0].nombre == "Pallof press")
    _, usos_con, ultima_con = pallof_fila_con
    assert usos_con == 3
    assert ultima_con == date(2026, 8, 18)


async def test_listar_filtrado_orden_uso(sesion: AsyncSession) -> None:
    """`orden='uso'` ordena por `usos DESC, nombre`."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    hip = await sesion.scalar(select(Ejercicio).where(Ejercicio.nombre == "Hip thrust"))
    assert pallof is not None and hip is not None
    usuario_id, tipo_sesion_id = await _ids_base(sesion)

    # Pallof: 3 usos. Hip thrust: 1 uso.
    for _ in range(3):
        await _crear_sesion_con_bloques(
            sesion, usuario_id, tipo_sesion_id, pallof.id, fecha=date(2026, 8, 10)
        )
    await _crear_sesion_con_bloques(
        sesion, usuario_id, tipo_sesion_id, hip.id, fecha=date(2026, 8, 11)
    )

    items, _ = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="uso",
    )
    pallof_idx = next(i for i, f in enumerate(items) if f[0].nombre == "Pallof press")
    hip_idx = next(i for i, f in enumerate(items) if f[0].nombre == "Hip thrust")
    assert pallof_idx < hip_idx
    assert items[pallof_idx][1] == 3
    assert items[hip_idx][1] == 1


async def test_listar_filtrado_orden_reciente(sesion: AsyncSession) -> None:
    """`orden='reciente'` ordena por `ultima_vez DESC NULLS LAST`."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    hip = await sesion.scalar(select(Ejercicio).where(Ejercicio.nombre == "Hip thrust"))
    assert pallof is not None and hip is not None
    usuario_id, tipo_sesion_id = await _ids_base(sesion)

    # Hip: ultima = 2026-08-20. Pallof: ultima = 2026-08-15.
    await _crear_sesion_con_bloques(
        sesion, usuario_id, tipo_sesion_id, pallof.id, fecha=date(2026, 8, 15)
    )
    await _crear_sesion_con_bloques(
        sesion, usuario_id, tipo_sesion_id, hip.id, fecha=date(2026, 8, 20)
    )

    items, _ = await repo_ejercicio.listar_filtrado(
        sesion,
        q=None,
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="reciente",
    )
    # Solo nos importan los dos que tienen uso.
    nombres_ordenados = [
        f[0].nombre for f in items if f[0].nombre in ("Pallof press", "Hip thrust")
    ]
    assert nombres_ordenados == ["Hip thrust", "Pallof press"]


# ---------------- repositorio R6.3 (detalle / historial / duplicados) ----


async def test_listar_historial_devuelve_top_5_ordenado_desc(
    sesion: AsyncSession,
) -> None:
    """Crea 7 ejecuciones del mismo ejercicio; `listar_historial(limite=5)`
    devuelve las 5 mas recientes ordenadas por fecha DESC."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    usuario_id, tipo_sesion_id = await _ids_base(sesion)

    for i in range(7):
        await _crear_sesion_con_bloques(
            sesion,
            usuario_id,
            tipo_sesion_id,
            pallof.id,
            fecha=date(2026, 7, 1 + i),
        )

    historial = await repo_ejercicio.listar_historial(sesion, pallof.id, limite=5)
    assert len(historial) == 5
    # El primero es el mas reciente: 2026-07-07.
    assert historial[0].fecha == date(2026, 7, 7)
    # Orden estrictamente descendente.
    fechas = [h.fecha for h in historial]
    assert fechas == sorted(fechas, reverse=True)


async def test_listar_historial_vacio_sin_usos(sesion: AsyncSession) -> None:
    """Un ejercicio nunca usado tiene historial vacio."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None

    historial = await repo_ejercicio.listar_historial(sesion, pallof.id, limite=5)
    assert historial == []


async def test_listar_posibles_duplicados_mismo_tipo_distinto_id(
    sesion: AsyncSession,
) -> None:
    """Candidatos a duplicado: mismo `tipo_medicion`, `id != self_id`,
    `activo = true`. No incluye al propio ni a los de otro tipo."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None

    # "Pallof Press" archivado y "Sentadilla explosiva" (mismo tipo carga) activo.
    sentadilla = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Sentadilla explosiva")
    )
    assert sentadilla is not None
    pallof.activo = False
    await sesion.flush()

    # Crear un candidato extra para asegurarnos de que filtra por activo=true.
    extra = await repo_ejercicio.crear(
        sesion,
        nombre="Pallof press variante",
        tipo_medicion=TipoMedicion.carga,
        descripcion=None,
    )
    await sesion.flush()

    candidatos = await repo_ejercicio.listar_posibles_duplicados(sesion, pallof)
    nombres = {c.id: c.nombre for c in candidatos}
    # El propio archivado NO debe aparecer.
    assert pallof.id not in nombres
    # El candidato activo del mismo tipo SI.
    assert extra.id in nombres
    # Sentadilla tambien (mismo tipo carga, activo).
    assert sentadilla.id in nombres


async def test_contar_usos_cuenta_filas_de_bloque(sesion: AsyncSession) -> None:
    """`contar_usos` cuenta filas de `bloque` (no `bloque_plan`). Crea 3
    sesiones con 2 bloques del mismo ejercicio = 6 usos."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    usuario_id, tipo_sesion_id = await _ids_base(sesion)

    for i in range(3):
        await _crear_sesion_con_bloques(
            sesion,
            usuario_id,
            tipo_sesion_id,
            pallof.id,
            fecha=date(2026, 8, 1 + i),
            cantidad_bloques=2,
            serie=1,
        )

    assert await repo_ejercicio.contar_usos(sesion, pallof.id) == 6


async def test_archivar_ejercicio_actualiza_activo(sesion: AsyncSession) -> None:
    """`archivar` es un UPDATE que pone `activo = false`. Verifica el flag."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    assert pallof.activo is True

    await repo_ejercicio.archivar(sesion, pallof)
    await sesion.flush()

    recargado = await sesion.get(Ejercicio, pallof.id)
    assert recargado is not None
    assert recargado.activo is False


# ------------------------------------------------ services R6.4 ----


async def test_listar_ejercicios_filtrado_service_normaliza_q(
    sesion: AsyncSession,
) -> None:
    """El service normaliza `q` antes de pasar al repo: ?q=hip thrust y
    ?q=HIP THRUST producen el mismo resultado. La busqueda ignora acentos
    via la traduccion SQL del repo."""
    from app.services.catalogo import entrenamiento as service

    minus = await service.listar_ejercicios_filtrado(
        sesion,
        q="hip thrust",
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    mayus = await service.listar_ejercicios_filtrado(
        sesion,
        q="HIP THRUST",
        tipo_medicion=None,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    assert minus.total == mayus.total
    assert minus.total >= 1
    nombres = {item.nombre for item in minus.items}
    assert "Hip thrust" in nombres


async def test_listar_ejercicios_filtrado_service_tipo_medicion(
    sesion: AsyncSession,
) -> None:
    """El service propaga el filtro de tipo_medicion al repo."""
    from app.services.catalogo import entrenamiento as service

    respuesta = await service.listar_ejercicios_filtrado(
        sesion,
        q=None,
        tipo_medicion=TipoMedicion.carga,
        tipo_sesion_id=None,
        activo=True,
        orden="nombre",
    )
    assert respuesta.total > 0
    assert all(item.tipo_medicion is TipoMedicion.carga for item in respuesta.items)


async def test_obtener_detalle_ejercicio_devuelve_historial_y_duplicados(
    sesion: AsyncSession,
) -> None:
    """Detalle completo: datos del ejercicio + historial top 5 + duplicados."""
    from app.services.catalogo import entrenamiento as service

    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    usuario_id, tipo_sesion_id = await _ids_base(sesion)

    # 2 ejecuciones del pallof + 1 con un ejercicio muy parecido.
    await _crear_sesion_con_bloques(
        sesion, usuario_id, tipo_sesion_id, pallof.id, fecha=date(2026, 8, 10)
    )
    await _crear_sesion_con_bloques(
        sesion, usuario_id, tipo_sesion_id, pallof.id, fecha=date(2026, 8, 15)
    )

    detalle = await service.obtener_detalle_ejercicio(sesion, pallof.id)

    assert detalle.id == pallof.id
    assert detalle.nombre == "Pallof press"
    assert len(detalle.historial) == 2
    # Orden por fecha desc: la primera es 2026-08-15.
    assert detalle.historial[0].fecha == date(2026, 8, 15)
    assert detalle.historial[1].fecha == date(2026, 8, 10)
    # El test no chequea duplicados (no hay un "Pallof press X" con similitud
    # >=0.75 en el seed). Eso se valida en el test siguiente con uno creado.


async def test_obtener_detalle_ejercicio_sin_uso_historial_vacio(
    sesion: AsyncSession,
) -> None:
    """Sin ejecuciones: historial vacio y posibles_duplicados puede ser
    [] o poblarse con candidatos segun el seed."""
    from app.services.catalogo import entrenamiento as service

    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None

    detalle = await service.obtener_detalle_ejercicio(sesion, pallof.id)
    assert detalle.historial == []
    # Sin semilla de duplicados no forzamos nada aca.


async def test_obtener_detalle_ejercicio_posibles_duplicados_075(
    sesion: AsyncSession,
) -> None:
    """Crea un ejercicio con similitud >=0.75 al Pallof press, verifica que
    aparece en `posibles_duplicados`. Otro con similitud baja (<0.75) NO
    aparece."""
    from app.services.catalogo import entrenamiento as service

    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None

    # "Pallof press inclinado" -> similitud >= 0.75 contra "Pallof press".
    candidato_alto = await repo_ejercicio.crear(
        sesion,
        nombre="Pallof press inclinado",
        tipo_medicion=TipoMedicion.carga,
        descripcion=None,
    )
    # Algo completamente distinto -> similitud muy baja. NO debe aparecer.
    await repo_ejercicio.crear(
        sesion,
        nombre="Sentadilla búlgara",
        tipo_medicion=TipoMedicion.carga,
        descripcion=None,
    )
    await sesion.flush()

    detalle = await service.obtener_detalle_ejercicio(sesion, pallof.id)
    nombres_dup = {d.nombre for d in detalle.posibles_duplicados}
    assert "Pallof press inclinado" in nombres_dup
    assert "Sentadilla búlgara" not in nombres_dup
    # El propio NO aparece.
    assert pallof.id not in {d.id for d in detalle.posibles_duplicados}
    # El candidato_alto tiene similitud reportada >= 0.75.
    cand = next(d for d in detalle.posibles_duplicados if d.id == candidato_alto.id)
    assert cand.similitud >= 0.75


async def test_obtener_detalle_ejercicio_404_si_no_existe(
    sesion: AsyncSession,
) -> None:
    """`RecursoNoEncontradoError` cuando el id no existe."""
    from app.core.exceptions import RecursoNoEncontradoError
    from app.services.catalogo import entrenamiento as service

    with pytest.raises(RecursoNoEncontradoError):
        await service.obtener_detalle_ejercicio(sesion, 99999)


# --------------------------------------------- router R6.5 ---


async def test_obtener_detalle_ejercicio_via_endpoint_devuelve_404(
    cliente: AsyncClient,
) -> None:
    """El endpoint tambien devuelve 404 cuando el id no existe."""
    respuesta = await cliente.get("/api/v1/catalogos/ejercicios/99999")
    assert respuesta.status_code == 404


async def test_obtener_detalle_ejercicio_via_endpoint_401_sin_token() -> None:
    """Sin token JWT el endpoint devuelve 401. `get_usuario_actual` rechaza
    requests sin credenciales."""
    from httpx import ASGITransport
    from httpx import AsyncClient as _AsyncClient

    from app.main import app as _app

    transport = ASGITransport(app=_app)
    async with _AsyncClient(transport=transport, base_url="http://test") as sin_auth:
        respuesta = await sin_auth.get("/api/v1/catalogos/ejercicios/1")
    assert respuesta.status_code == 401


async def test_listar_ejercicios_filtrado_via_endpoint(
    cliente: AsyncClient,
) -> None:
    """El endpoint GET /catalogos/ejercicios devuelve el envelope
    `EjercicioListRead` con `items` y `total`."""
    respuesta = await cliente.get("/api/v1/catalogos/ejercicios")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert "items" in cuerpo
    assert "total" in cuerpo
    assert cuerpo["total"] == 29
    assert len(cuerpo["items"]) == 29
    item = cuerpo["items"][0]
    assert "usos" in item
    assert "ultima_vez" in item
    assert "activo" in item


async def test_listar_ejercicios_filtrado_via_endpoint_q_con_acentos(
    cliente: AsyncClient,
) -> None:
    """`?q=elevacion` y `?q=elevación` matchean el mismo ejercicio via el
    endpoint. La normalizacion vive en el service."""
    sin = await cliente.get("/api/v1/catalogos/ejercicios", params={"q": "elevacion"})
    con = await cliente.get("/api/v1/catalogos/ejercicios", params={"q": "elevación"})
    assert sin.status_code == 200
    assert con.status_code == 200
    assert sin.json()["total"] == con.json()["total"] >= 1


async def test_listar_ejercicios_filtrado_via_endpoint_tipo_medicion(
    cliente: AsyncClient,
) -> None:
    """`?tipo_medicion=carga` filtra via el endpoint."""
    respuesta = await cliente.get(
        "/api/v1/catalogos/ejercicios", params={"tipo_medicion": "carga"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] > 0
    assert all(item["tipo_medicion"] == "carga" for item in cuerpo["items"])


async def test_listar_ejercicios_filtrado_via_endpoint_orden_uso(
    cliente: AsyncClient,
) -> None:
    """`?orden=uso` es aceptado por el endpoint sin 422."""
    respuesta = await cliente.get(
        "/api/v1/catalogos/ejercicios", params={"orden": "uso"}
    )
    assert respuesta.status_code == 200


async def test_obtener_detalle_ejercicio_via_endpoint_devuelve_historial_y_duplicados(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """El endpoint GET /catalogos/ejercicios/{id} devuelve el detalle completo."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    await _crear_sesion_con_bloques(
        sesion, usuario_id, tipo_sesion_id, pallof.id, fecha=date(2026, 8, 10)
    )

    respuesta = await cliente.get(f"/api/v1/catalogos/ejercicios/{pallof.id}")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["id"] == pallof.id
    assert cuerpo["nombre"] == "Pallof press"
    assert "historial" in cuerpo
    assert "posibles_duplicados" in cuerpo
    assert len(cuerpo["historial"]) == 1
    assert cuerpo["historial"][0]["fecha"] == "2026-08-10"


# ------------------------- POST /catalogos/ejercicios (R6.5) ---


async def test_crear_ejercicio_exige_tipo_medicion(cliente: AsyncClient) -> None:
    """POST sin tipo_medicion devuelve 422."""
    respuesta = await cliente.post(
        "/api/v1/catalogos/ejercicios",
        json={"nombre": "Nuevo ejercicio"},
    )
    assert respuesta.status_code == 422


async def test_crear_ejercicio_con_patron_y_carga_lumbar(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """POST con patron + carga_lumbar los persiste."""
    respuesta = await cliente.post(
        "/api/v1/catalogos/ejercicios",
        json={
            "nombre": "Pallof press con banda",
            "tipo_medicion": "carga",
            "patron": "core_antirotacion",
            "carga_lumbar": "baja",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Pallof press con banda"
    assert cuerpo["patron"] == "core_antirotacion"
    assert cuerpo["carga_lumbar"] == "baja"
    assert cuerpo["tipo_medicion"] == "carga"


async def test_crear_ejercicio_nombre_duplicado_409(
    cliente: AsyncClient,
) -> None:
    """POST con un nombre que ya existe (normalizado) devuelve 409."""
    primero = await cliente.post(
        "/api/v1/catalogos/ejercicios",
        json={"nombre": "Pallof press X", "tipo_medicion": "carga"},
    )
    assert primero.status_code == 200

    segundo = await cliente.post(
        "/api/v1/catalogos/ejercicios",
        json={"nombre": "pallof PRESS x", "tipo_medicion": "carga"},
    )
    assert segundo.status_code == 409


# ------------------------- PATCH /catalogos/ejercicios/{id} ---


async def test_patch_ejercicio_acepta_patron_carga_lumbar_activo(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """PATCH actualiza los campos nuevos (patron, carga_lumbar, activo)."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None

    respuesta = await cliente.patch(
        f"/api/v1/catalogos/ejercicios/{pallof.id}",
        json={"patron": "core_pasada", "carga_lumbar": "alta", "activo": False},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["patron"] == "core_pasada"
    assert cuerpo["carga_lumbar"] == "alta"
    assert cuerpo["activo"] is False


async def test_patch_ejercicio_rechaza_tipo_medicion_422(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """PATCH con `tipo_medicion` devuelve 422 (Pydantic extra=forbid)."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None

    respuesta = await cliente.patch(
        f"/api/v1/catalogos/ejercicios/{pallof.id}",
        json={"tipo_medicion": "carga"},
    )
    assert respuesta.status_code == 422


async def test_patch_ejercicio_nombre_duplicado_normalizado_409(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """PATCH con un nombre que colisiona con otro activo (normalizado)
    devuelve 409, no 200 silencioso."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None

    respuesta = await cliente.patch(
        f"/api/v1/catalogos/ejercicios/{pallof.id}",
        json={"nombre": "HIP THRUST"},
    )
    assert respuesta.status_code == 409


async def test_patch_ejercicio_parcial_no_toca_omitidos(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """PATCH con un solo campo no toca los demas."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    patron_inicial = pallof.patron
    activo_inicial = pallof.activo

    respuesta = await cliente.patch(
        f"/api/v1/catalogos/ejercicios/{pallof.id}",
        json={"descripcion": "Solo cambia descripcion"},
    )
    assert respuesta.status_code == 200
    await sesion.refresh(pallof)
    assert pallof.descripcion == "Solo cambia descripcion"
    assert pallof.patron == patron_inicial
    assert pallof.activo is activo_inicial


async def test_patch_ejercicio_descripcion_vacia_pone_null(
    cliente: AsyncClient, sesion: AsyncSession
) -> None:
    """PATCH con descripcion='' la traduce a NULL en la base."""
    pallof = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.nombre == "Pallof press")
    )
    assert pallof is not None
    pallof.descripcion = "Algo que estaba"
    await sesion.flush()

    respuesta = await cliente.patch(
        f"/api/v1/catalogos/ejercicios/{pallof.id}",
        json={"descripcion": ""},
    )
    assert respuesta.status_code == 200
    await sesion.refresh(pallof)
    assert pallof.descripcion is None


async def test_patch_ejercicio_404_si_no_existe(cliente: AsyncClient) -> None:
    respuesta = await cliente.patch(
        "/api/v1/catalogos/ejercicios/99999",
        json={"descripcion": "nada"},
    )
    assert respuesta.status_code == 404


async def test_patch_ejercicio_401_sin_token() -> None:
    """Sin token JWT el endpoint PATCH devuelve 401."""
    from httpx import ASGITransport
    from httpx import AsyncClient as _AsyncClient

    from app.main import app as _app

    transport = ASGITransport(app=_app)
    async with _AsyncClient(transport=transport, base_url="http://test") as sin_auth:
        respuesta = await sin_auth.patch(
            "/api/v1/catalogos/ejercicios/1",
            json={"descripcion": "x"},
        )
    assert respuesta.status_code == 401


if __name__ == "__main__":
    # Permite correr este archivo aislado: `pytest tests/test_banco_ejercicios.py`.
    pytest.main([__file__, "-q"])
