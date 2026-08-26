"""Tests del detalle de plan (PR 5 del feature 2, R9).

Cubre:
- R9.1: schemas de detalle de plan (`PlanDetalleRead` + `BloquePlanDetalleRead`
  + `PlanCicloRead`) — son la forma que devuelve `GET /planes/{id}` (SPEC §3.8).
- R9.2: repositorio `obtener_con_detalle` para plan (selectinload de bloques
  planeados + ciclo_semana + ciclo).
- R9.3: service `obtener_plan_detalle` (shape completo, ciclo opcional, 404).
- R9.4: router `GET /planes/{id}` → `PlanDetalleRead`.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import (
    BloquePlan,
    Ciclo,
    CicloSemana,
    Ejercicio,
    SesionPlan,
    TipoSesion,
    Usuario,
)
from app.models.enums import EstadoSesionPlan, FaseCiclo, TipoMedicion

# ============================================================ fixtures =====


@pytest.fixture
async def cliente(sesion: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP con la sesion de pytest y el usuario seed autenticado."""
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


async def _ejercicio_de_medicion(
    sesion: AsyncSession, tipo_medicion: TipoMedicion
) -> Ejercicio:
    ejercicio = await sesion.scalar(
        select(Ejercicio).where(Ejercicio.tipo_medicion == tipo_medicion)
    )
    assert ejercicio is not None, f"no hay ejercicio sembrado de tipo {tipo_medicion}"
    return ejercicio


# =================================================== R9.1 schemas (RED) =====


def test_schema_plan_detalle_incluye_ciclo_y_bloques_planeados() -> None:
    """`PlanDetalleRead` (R9.1) agrupa: cabecera del plan + `ciclo` (anidado
    opcional) + `bloques_planeados` (lista). Su forma es la del endpoint
    `GET /planes/{id}` (SPEC §3.8): sin `usuario_id` ni `sesion_id`
    intermedio, con la info que ve el usuario antes de ejecutar la sesion."""
    from app.schemas.entrenamiento.plan import PlanDetalleRead

    plan = PlanDetalleRead(
        id=7,
        usuario_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        ciclo_semana_id=3,
        ciclo=None,
        fecha_prevista=date(2026, 8, 10),
        dia_sugerido=2,
        tipo_sesion_id=1,
        objetivo="fuerza full-body",
        duracion_min_est=50,
        rpe_objetivo=7,
        estado=EstadoSesionPlan.pendiente,
        clave_import="2-fuerza",
        nombre="Fuerza full-body",
        nota="foco en técnica",
        bloques_planeados=[],
    )
    assert plan.id == 7
    assert plan.ciclo_semana_id == 3
    assert plan.ciclo is None  # sin ciclo_semana cargada
    assert plan.estado is EstadoSesionPlan.pendiente
    assert plan.bloques_planeados == []
    # Tipo del shape: el endpoint lo serializa via este schema.
    assert isinstance(plan.bloques_planeados, list)


def test_schema_bloque_plan_detalle_incluye_ejercicio_y_objetivos() -> None:
    """`BloquePlanDetalleRead` (R9.1) reune: campos del bloque_plan +
    `ejercicio` anidado (subset de `EjercicioRead`). El `ejercicio` se
    reutiliza del subset `BloqueEjercicioEnDetalleRead` que ya usa el
    detalle de sesion (R8.1)."""
    from app.schemas.entrenamiento.plan import BloquePlanDetalleRead
    from app.schemas.entrenamiento.sesion import BloqueEjercicioEnDetalleRead

    bloque = BloquePlanDetalleRead(
        id=99,
        sesion_plan_id=7,
        orden=1,
        series=3,
        reps_min=6,
        reps_max=8,
        peso_objetivo_kg=Decimal("80.0"),
        distancia_objetivo_m=None,
        duracion_objetivo_s=None,
        nota="al 6-8 reps",
        ejercicio=BloqueEjercicioEnDetalleRead(
            id=12,
            nombre="Hip thrust",
            tipo_medicion=TipoMedicion.carga,
            descripcion="cadera al techo",
            carga_lumbar="media",
        ),
    )
    assert bloque.id == 99
    assert bloque.sesion_plan_id == 7
    assert bloque.orden == 1
    assert bloque.series == 3
    assert bloque.reps_min == 6
    assert bloque.reps_max == 8
    assert bloque.peso_objetivo_kg == Decimal("80.0")
    assert bloque.nota == "al 6-8 reps"
    assert bloque.ejercicio.nombre == "Hip thrust"
    assert bloque.ejercicio.tipo_medicion is TipoMedicion.carga


# ========================================== R9.2 repositorio plan detalle ====


async def test_repo_obtener_plan_con_detalle_carga_bloques_y_ciclo(
    sesion: AsyncSession,
) -> None:
    """`obtener_con_detalle` para plan precarga: `bloques_planeados` (con su
    `ejercicio` anidado) + `ciclo_semana` + `ciclo` de esa semana. Sin
    `ciclo_semana_id`, `ciclo_semana` queda None sin disparar queries
    adicionales."""
    from app.repositories.entrenamiento.plan import obtener_con_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)

    ciclo = Ciclo(
        usuario_id=usuario_id,
        numero=1,
        objetivo="base",
        fecha_inicio=date(2026, 8, 3),  # lunes
        semanas=4,
    )
    sesion.add(ciclo)
    await sesion.flush()
    semana = CicloSemana(
        ciclo_id=ciclo.id,
        numero=1,
        fase=FaseCiclo.carga,
        rpe_objetivo_min=6,
        rpe_objetivo_max=8,
    )
    sesion.add(semana)
    await sesion.flush()

    plan = SesionPlan(
        usuario_id=usuario_id,
        ciclo_semana_id=semana.id,
        fecha_prevista=date(2026, 8, 5),
        dia_sugerido=2,
        tipo_sesion_id=tipo_sesion_id,
        objetivo="fuerza full-body",
        duracion_min_est=50,
        rpe_objetivo=7,
        estado=EstadoSesionPlan.pendiente,
        nombre="Fuerza full-body",
        clave_import="2-fuerza",
    )
    sesion.add(plan)
    await sesion.flush()
    sesion.add(
        BloquePlan(
            sesion_plan_id=plan.id,
            ejercicio_id=ejercicio.id,
            orden=1,
            series=3,
            reps_min=6,
            reps_max=8,
            peso_objetivo_kg=Decimal("80.0"),
            nota="al 6-8 reps",
        )
    )
    await sesion.flush()

    cargada = await obtener_con_detalle(sesion, plan.id)

    assert cargada is not None
    assert cargada.id == plan.id
    # Bloques planeados (1) con su ejercicio ya cargado.
    assert len(cargada.bloques_planeados) == 1
    assert cargada.bloques_planeados[0].ejercicio.id == ejercicio.id
    assert cargada.bloques_planeados[0].ejercicio.tipo_medicion is TipoMedicion.carga
    # Ciclo_semana + ciclo anidados.
    assert cargada.ciclo_semana is not None
    assert cargada.ciclo_semana.ciclo is not None
    assert cargada.ciclo_semana.ciclo.numero == 1
    assert cargada.ciclo_semana.fase is FaseCiclo.carga


# =================================================== R9.3 service =========


async def test_plan_detalle_shape_completo(sesion: AsyncSession) -> None:
    """`obtener_plan_detalle` devuelve un `PlanDetalleRead` con cabecera del
    plan + `ciclo` (anidado) + `bloques_planeados` (3 bloques con su
    ejercicio)."""
    from app.services.entrenamiento.plan import obtener_plan_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)

    ciclo = Ciclo(
        usuario_id=usuario_id,
        numero=2,
        objetivo="potencia",
        fecha_inicio=date(2026, 8, 3),
        semanas=4,
    )
    sesion.add(ciclo)
    await sesion.flush()
    semana = CicloSemana(
        ciclo_id=ciclo.id,
        numero=2,
        fase=FaseCiclo.carga,
        rpe_objetivo_min=7,
        rpe_objetivo_max=9,
    )
    sesion.add(semana)
    await sesion.flush()

    plan = SesionPlan(
        usuario_id=usuario_id,
        ciclo_semana_id=semana.id,
        fecha_prevista=date(2026, 8, 12),
        dia_sugerido=2,
        tipo_sesion_id=tipo_sesion_id,
        objetivo="fuerza full-body",
        duracion_min_est=50,
        rpe_objetivo=8,
        estado=EstadoSesionPlan.pendiente,
        clave_import="2-fuerza",
        nombre="Fuerza full-body",
        nota="nota del plan",
    )
    sesion.add(plan)
    await sesion.flush()
    for orden in (1, 2, 3):
        sesion.add(
            BloquePlan(
                sesion_plan_id=plan.id,
                ejercicio_id=ejercicio.id,
                orden=orden,
                series=3,
                reps_min=6,
                reps_max=8,
                peso_objetivo_kg=Decimal("80.0"),
                nota=f"bloque {orden}",
            )
        )
    await sesion.flush()

    detalle = await obtener_plan_detalle(sesion, usuario_id, plan.id)

    # Cabecera del plan.
    assert detalle.id == plan.id
    assert detalle.usuario_id == usuario_id
    assert detalle.ciclo_semana_id == semana.id
    assert detalle.fecha_prevista == date(2026, 8, 12)
    assert detalle.dia_sugerido == 2
    assert detalle.tipo_sesion_id == tipo_sesion_id
    assert detalle.objetivo == "fuerza full-body"
    assert detalle.duracion_min_est == 50
    assert detalle.rpe_objetivo == 8
    assert detalle.estado is EstadoSesionPlan.pendiente
    assert detalle.clave_import == "2-fuerza"
    assert detalle.nombre == "Fuerza full-body"
    assert detalle.nota == "nota del plan"
    # Ciclo anidado con numero/semana/fase del plan.
    assert detalle.ciclo is not None
    assert detalle.ciclo.numero == 2
    assert detalle.ciclo.semana == 2
    assert detalle.ciclo.fase is FaseCiclo.carga
    # 3 bloques planeados, ordenados asc por `orden`, con ejercicio anidado.
    assert len(detalle.bloques_planeados) == 3
    assert [b.orden for b in detalle.bloques_planeados] == [1, 2, 3]
    for bloque in detalle.bloques_planeados:
        assert bloque.ejercicio.id == ejercicio.id
        assert bloque.ejercicio.tipo_medicion is TipoMedicion.carga
        assert bloque.series == 3
        assert bloque.reps_min == 6
        assert bloque.reps_max == 8


async def test_plan_detalle_sin_ciclo_devuelve_ciclo_null(
    sesion: AsyncSession,
) -> None:
    """Plan huerfano (sin `ciclo_semana_id`): `detalle.ciclo is None` y
    `detalle.bloques_planeados` sigue funcionando."""
    from app.services.entrenamiento.plan import obtener_plan_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)
    plan = SesionPlan(
        usuario_id=usuario_id,
        ciclo_semana_id=None,
        tipo_sesion_id=tipo_sesion_id,
        objetivo="libre",
    )
    sesion.add(plan)
    await sesion.flush()
    sesion.add(
        BloquePlan(
            sesion_plan_id=plan.id,
            ejercicio_id=ejercicio.id,
            orden=1,
            series=3,
            reps_min=8,
            reps_max=10,
        )
    )
    await sesion.flush()

    detalle = await obtener_plan_detalle(sesion, usuario_id, plan.id)

    assert detalle.ciclo is None
    assert detalle.ciclo_semana_id is None
    assert len(detalle.bloques_planeados) == 1
    assert detalle.bloques_planeados[0].ejercicio.id == ejercicio.id


async def test_plan_detalle_404_si_no_existe(sesion: AsyncSession) -> None:
    """`obtener_plan_detalle` levanta `RecursoNoEncontradoError` si el plan
    no existe."""
    from app.core.exceptions import RecursoNoEncontradoError
    from app.services.entrenamiento.plan import obtener_plan_detalle

    usuario_id, _ = await _ids_base(sesion)
    with pytest.raises(RecursoNoEncontradoError):
        await obtener_plan_detalle(sesion, usuario_id, 999_999)


async def test_plan_detalle_404_si_no_es_del_usuario(sesion: AsyncSession) -> None:
    """Aunque el plan exista, si pertenece a otro usuario: 404 (no se filtra
    la existencia, AGENTS §5)."""
    from app.core.exceptions import RecursoNoEncontradoError
    from app.services.entrenamiento.plan import obtener_plan_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    plan = SesionPlan(usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id)
    sesion.add(plan)
    await sesion.flush()

    otro_usuario_id = uuid.uuid4()
    with pytest.raises(RecursoNoEncontradoError):
        await obtener_plan_detalle(sesion, otro_usuario_id, plan.id)


async def test_plan_detalle_401_sin_token() -> None:
    """Sin Authorization: 401 (la dependencia `get_usuario_actual` rechaza)."""
    from httpx import ASGITransport

    from app.main import app as _app

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as sin_auth:
        respuesta = await sin_auth.get("/api/v1/planes/1")
    assert respuesta.status_code == 401


async def test_plan_detalle_campos_opcionales_son_none_si_null(
    sesion: AsyncSession,
) -> None:
    """Plan con todos los opcionales NULL (clave_import, fecha_prevista,
    dia_sugerido, objetivo, duracion_min_est, rpe_objetivo, nombre, nota):
    todos se exponen como None en el detalle."""
    from app.services.entrenamiento.plan import obtener_plan_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    plan = SesionPlan(usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id)
    sesion.add(plan)
    await sesion.flush()

    detalle = await obtener_plan_detalle(sesion, usuario_id, plan.id)

    assert detalle.clave_import is None
    assert detalle.fecha_prevista is None
    assert detalle.dia_sugerido is None
    assert detalle.objetivo is None
    assert detalle.duracion_min_est is None
    assert detalle.rpe_objetivo is None
    assert detalle.nombre is None
    assert detalle.nota is None
    # ciclo_semana_id es None → ciclo anidado None.
    assert detalle.ciclo_semana_id is None
    assert detalle.ciclo is None
    # estado cae al default del server: pendiente.
    assert detalle.estado is EstadoSesionPlan.pendiente


# =================================================== R9.4 router ===========


async def test_router_get_plan_detalle_devuelve_plan_detalle_read(
    sesion: AsyncSession,
    cliente: AsyncClient,
) -> None:
    """`GET /planes/{plan_id}` devuelve un `PlanDetalleRead` con `ciclo`
    anidado y `bloques_planeados` (cada uno con `ejercicio`)."""
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)

    ciclo = Ciclo(
        usuario_id=usuario_id,
        numero=1,
        objetivo="base",
        fecha_inicio=date(2026, 8, 3),
        semanas=4,
    )
    sesion.add(ciclo)
    await sesion.flush()
    semana = CicloSemana(
        ciclo_id=ciclo.id,
        numero=1,
        fase=FaseCiclo.carga,
        rpe_objetivo_min=6,
        rpe_objetivo_max=8,
    )
    sesion.add(semana)
    await sesion.flush()

    plan = SesionPlan(
        usuario_id=usuario_id,
        ciclo_semana_id=semana.id,
        tipo_sesion_id=tipo_sesion_id,
        objetivo="full-body",
        duracion_min_est=50,
        rpe_objetivo=7,
        estado=EstadoSesionPlan.pendiente,
        nombre="Fuerza full-body",
    )
    sesion.add(plan)
    await sesion.flush()
    sesion.add(
        BloquePlan(
            sesion_plan_id=plan.id,
            ejercicio_id=ejercicio.id,
            orden=1,
            series=3,
            reps_min=6,
            reps_max=8,
            peso_objetivo_kg=Decimal("80.0"),
        )
    )
    await sesion.flush()

    respuesta = await cliente.get(f"/api/v1/planes/{plan.id}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == plan.id
    assert cuerpo["estado"] == "pendiente"
    assert cuerpo["duracion_min_est"] == 50
    assert cuerpo["rpe_objetivo"] == 7
    assert cuerpo["ciclo"]["numero"] == 1
    assert cuerpo["ciclo"]["semana"] == 1
    assert cuerpo["ciclo"]["fase"] == "carga"
    assert len(cuerpo["bloques_planeados"]) == 1
    assert cuerpo["bloques_planeados"][0]["orden"] == 1
    assert cuerpo["bloques_planeados"][0]["series"] == 3
    assert cuerpo["bloques_planeados"][0]["ejercicio"]["id"] == ejercicio.id
    assert cuerpo["bloques_planeados"][0]["ejercicio"]["nombre"] == ejercicio.nombre


async def test_router_get_plan_detalle_404_si_no_existe(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.get("/api/v1/planes/999999")
    assert respuesta.status_code == 404
