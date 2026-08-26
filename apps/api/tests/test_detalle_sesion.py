"""Tests del detalle de sesion (PR 4 del feature 2, R8).

Cubre:
- R8.1: schemas de detalle (SesionDetalleRead + subsets anidados).
- R8.2: repositorio `obtener_con_detalle` (selectinload de los 3 niveles).
- R8.3: repositorio `listar_por_usuario_y_fecha` para molestias.
- R8.4: service `obtener_sesion_detalle` (shape completo, sesion libre,
  orden de bloques, bloques no ejecutados, delta de bloque y sesion).
- R8.5: router GET /sesiones/{id} → SesionDetalleRead.
- R8.6: regresion N+1 con `contador_queries`.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import (
    BloquePlan,
    Ciclo,
    CicloSemana,
    Ejercicio,
    Molestia,
    Sesion,
    SesionPlan,
    TipoSesion,
    Usuario,
    ZonaCorporal,
)
from app.models.enums import EstadoSesionPlan, FaseCiclo, TipoMedicion
from app.repositories import entrenamiento as repo
from app.repositories.bienestar import molestia as repo_molestia
from app.repositories.entrenamiento import sesion as repo_sesion
from app.schemas.entrenamiento.sesion import (
    BloqueDeltaRead,
    BloqueDetalleRead,
    BloqueEjercicioEnDetalleRead,
    BloqueNoEjecutadoRead,
    BloqueObjetivoRead,
    SesionDeltaRead,
    SesionDetalleRead,
    SesionTipoRead,
)

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


async def _crear_sesion_simple(
    sesion: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    tipo_sesion_id: int,
    sesion_plan_id: int | None = None,
    fecha: date | None = None,
    duracion_min: int = 60,
    rpe: int = 7,
    nota: str | None = None,
) -> Sesion:
    """Crea una sesion sin bloques. El test agrega bloques / plan por separado."""
    return await repo_sesion.crear(
        sesion,
        sesion_id=uuid.uuid4(),
        idempotency_key=uuid.uuid4(),
        usuario_id=usuario_id,
        sesion_plan_id=sesion_plan_id,
        fecha=fecha or date(2026, 8, 24),
        tipo_sesion_id=tipo_sesion_id,
        duracion_min=duracion_min,
        rpe=rpe,
        nota=nota,
    )


# =================================================== R8.1 schemas (RED) =====


def test_schema_sesion_detalle_tiene_campos_basicos() -> None:
    """El envelope del detalle de sesion tiene: id, fecha, tipo_sesion
    (anidado), duracion_min, rpe, carga_srpe, nota, plan (opcional), delta
    (opcional), bloques y bloques_no_ejecutados (listas), molestias."""
    detalle = SesionDetalleRead(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        usuario_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        sesion_plan_id=None,
        fecha=date(2026, 8, 24),
        tipo_sesion=SesionTipoRead(id=1, codigo="fuerza", nombre="Fuerza"),
        duracion_min=55,
        rpe=8,
        nota="buena",
        carga_srpe=440,
        registrado_en=datetime(2026, 8, 24, 18, 0, tzinfo=UTC),
        plan=None,
        delta=None,
        bloques=[],
        bloques_no_ejecutados=[],
        molestias=[],
    )
    assert detalle.id == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert detalle.tipo_sesion.codigo == "fuerza"
    assert detalle.duracion_min == 55
    assert detalle.carga_srpe == 440
    assert detalle.bloques == []
    assert detalle.bloques_no_ejecutados == []
    assert detalle.molestias == []
    assert detalle.plan is None
    assert detalle.delta is None


def test_schema_bloque_detalle_tiene_ejercicio_objetivo_delta() -> None:
    """`BloqueDetalleRead` agrupa: campos del bloque + ejercicio (subset)
    + objetivo (subset opcional) + delta. Sin objetivo → `objetivo=None`."""
    bloque = BloqueDetalleRead(
        id=101,
        sesion_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        orden=1,
        series=3,
        reps=8,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("80.0"),
        rpe=8,
        dolor_lumbar=False,
        nota="técnica ok",
        ejercicio=BloqueEjercicioEnDetalleRead(
            id=12,
            nombre="Hip thrust",
            tipo_medicion=TipoMedicion.carga,
            descripcion="cadera al techo",
            carga_lumbar="media",
        ),
        objetivo=None,
        delta=BloqueDeltaRead(
            series=0,
            reps=0,
            peso_kg=Decimal("-10"),
            distancia_m=None,
            duracion_s=None,
        ),
    )
    assert bloque.id == 101
    assert bloque.orden == 1
    assert bloque.ejercicio.nombre == "Hip thrust"
    assert bloque.ejercicio.tipo_medicion is TipoMedicion.carga
    assert bloque.ejercicio.carga_lumbar == "media"
    assert bloque.objetivo is None
    assert bloque.delta.peso_kg == Decimal("-10")


def test_schema_bloque_no_ejecutado_tiene_orden_ejercicio_objetivo() -> None:
    """Los bloques que estaban en el plan pero no se ejecutaron: solo
    `orden`, `ejercicio_id`, `ejercicio_nombre` y `objetivo` (subset del
    bloque_plan)."""
    objetivo = BloqueObjetivoRead(
        id=42,
        orden=2,
        series=3,
        reps_min=8,
        reps_max=10,
        peso_objetivo_kg=Decimal("80.0"),
        distancia_objetivo_m=None,
        duracion_objetivo_s=None,
        nota="bird-dog",
    )
    no_ejecutado = BloqueNoEjecutadoRead(
        orden=2,
        ejercicio_id=40,
        ejercicio_nombre="Bird-dog",
        objetivo=objetivo,
    )
    assert no_ejecutado.orden == 2
    assert no_ejecutado.ejercicio_id == 40
    assert no_ejecutado.ejercicio_nombre == "Bird-dog"
    assert no_ejecutado.objetivo.reps_min == 8
    assert no_ejecutado.objetivo.reps_max == 10


def test_schema_sesion_delta_tiene_duracion_rpe_carga() -> None:
    """El delta de sesion (sin envolver la sesion entera) tiene los 3 campos
    del SPEC: duracion_min, rpe, carga_srpe. Todos opcionales: si falta el
    plan, el servicio devuelve None en lugar de un SesionDeltaRead con
    campos NULL."""
    delta = SesionDeltaRead(duracion_min=5, rpe=2, carga_srpe=110)
    assert delta.duracion_min == 5
    assert delta.rpe == 2
    assert delta.carga_srpe == 110


# ========================================= R8.2 repositorio sesion detalle ====


async def test_repo_obtener_con_detalle_carga_sesion_bloques_ejercicio_tipo_sesion(
    sesion: AsyncSession,
) -> None:
    """`obtener_con_detalle` precarga 3 niveles via selectinload: sesion +
    bloques + ejercicio de cada bloque + tipo_sesion. Si no hay plan, el
    `sesion_plan` queda None sin disparar queries adicionales."""
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)

    sesion_creada = await _crear_sesion_simple(
        sesion, usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=8,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("80.0"),
        rpe=8,
        dolor_lumbar=False,
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=2,
        series=3,
        reps=8,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("80.0"),
        rpe=8,
        dolor_lumbar=False,
    )

    cargada = await repo_sesion.obtener_con_detalle(sesion, sesion_creada.id)

    assert cargada is not None
    assert cargada.id == sesion_creada.id
    # Bloques: ordenados por `Bloque.orden` (definido en el modelo).
    assert [b.orden for b in cargada.bloques] == [1, 2]
    # Cada bloque trae su `ejercicio` ya cargado (sin lazy-load posterior).
    assert cargada.bloques[0].ejercicio.id == ejercicio.id
    assert cargada.bloques[0].ejercicio.tipo_medicion is TipoMedicion.carga
    assert cargada.bloques[1].ejercicio.nombre == ejercicio.nombre
    # tipo_sesion anidado.
    assert cargada.tipo_sesion is not None
    assert cargada.tipo_sesion.id == tipo_sesion_id
    # sin plan: la relacion queda None (no se cargo el plan).
    assert cargada.sesion_plan_id is None
    assert cargada.sesion_plan is None


async def test_repo_obtener_con_detalle_carga_plan_si_existe(
    sesion: AsyncSession,
) -> None:
    """Sesion con `sesion_plan_id` → el plan se carga con sus bloques
    planeados y el ejercicio de cada uno."""
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
        estado=EstadoSesionPlan.cumplido,
        nombre="Fuerza full-body",
        nota="domingo antes del partido",
    )
    sesion.add(plan)
    await sesion.flush()

    bloque_plan = BloquePlan(
        sesion_plan_id=plan.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps_min=6,
        reps_max=8,
        peso_objetivo_kg=Decimal("90.0"),
        nota="al 6-8 reps",
    )
    sesion.add(bloque_plan)
    await sesion.flush()

    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
        fecha=date(2026, 8, 5),
        duracion_min=55,
        rpe=9,
    )

    cargada = await repo_sesion.obtener_con_detalle(sesion, sesion_creada.id)

    assert cargada is not None
    assert cargada.sesion_plan is not None
    assert cargada.sesion_plan.id == plan.id
    assert cargada.sesion_plan.nombre == "Fuerza full-body"
    assert cargada.sesion_plan.estado is EstadoSesionPlan.cumplido
    assert cargada.sesion_plan.duracion_min_est == 50
    assert cargada.sesion_plan.rpe_objetivo == 7
    assert len(cargada.sesion_plan.bloques_planeados) == 1
    assert cargada.sesion_plan.bloques_planeados[0].ejercicio.id == ejercicio.id
    assert cargada.sesion_plan.bloques_planeados[0].peso_objetivo_kg == Decimal("90.0")
    assert cargada.sesion_plan.bloques_planeados[0].reps_min == 6
    assert cargada.sesion_plan.bloques_planeados[0].reps_max == 8


async def test_repo_obtener_con_detalle_sin_plan_no_falla(
    sesion: AsyncSession,
) -> None:
    """`Sesion.sesion_plan_id` es nullable y UNIQUE simultaneamente: una
    sesion libre (sin plan) no debe romper el repo. Devuelve `sesion_plan =
    None` sin disparar lazy-loads."""
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    sesion_creada = await _crear_sesion_simple(
        sesion, usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id
    )

    cargada = await repo_sesion.obtener_con_detalle(sesion, sesion_creada.id)

    assert cargada is not None
    assert cargada.sesion_plan is None
    assert cargada.sesion_plan_id is None


async def test_repo_obtener_con_detalle_carga_ciclo_del_plan(
    sesion: AsyncSession,
) -> None:
    """El ciclo y la ciclo_semana del plan se cargan tambien: el detalle los
    expone via `plan.ciclo` y `plan.ciclo.semana`."""
    usuario_id, tipo_sesion_id = await _ids_base(sesion)

    ciclo = Ciclo(
        usuario_id=usuario_id,
        numero=2,
        objetivo="fuerza + potencia",
        fecha_inicio=date(2026, 8, 3),
        semanas=4,
    )
    sesion.add(ciclo)
    await sesion.flush()
    semana = CicloSemana(
        ciclo_id=ciclo.id,
        numero=1,
        fase=FaseCiclo.readaptacion,
        rpe_objetivo_min=5,
        rpe_objetivo_max=7,
    )
    sesion.add(semana)
    await sesion.flush()

    plan = SesionPlan(
        usuario_id=usuario_id,
        ciclo_semana_id=semana.id,
        tipo_sesion_id=tipo_sesion_id,
        objetivo="readaptacion",
        duracion_min_est=45,
        rpe_objetivo=6,
        estado=EstadoSesionPlan.cumplido,
    )
    sesion.add(plan)
    await sesion.flush()

    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
        fecha=date(2026, 8, 4),
        duracion_min=45,
        rpe=6,
    )

    cargada = await repo_sesion.obtener_con_detalle(sesion, sesion_creada.id)

    assert cargada is not None
    assert cargada.sesion_plan is not None
    assert cargada.sesion_plan.ciclo_semana is not None
    assert cargada.sesion_plan.ciclo_semana.ciclo is not None
    assert cargada.sesion_plan.ciclo_semana.ciclo.numero == 2
    assert cargada.sesion_plan.ciclo_semana.ciclo.objetivo == "fuerza + potencia"
    assert cargada.sesion_plan.ciclo_semana.fase is FaseCiclo.readaptacion
    assert cargada.sesion_plan.ciclo_semana.rpe_objetivo_min == 5
    assert cargada.sesion_plan.ciclo_semana.rpe_objetivo_max == 7


# =========================================== R8.3 repo molestias ==========


async def test_repositorio_molestias_por_usuario_y_fecha_devuelve_las_del_dia(
    sesion: AsyncSession,
) -> None:
    """`listar_por_usuario_y_fecha` filtra por usuario y fecha exactos,
    ordena por id ASC y trae la `zona` anidada (selectinload)."""
    usuario_id, _ = await _ids_base(sesion)
    zona1 = await sesion.scalar(
        select(ZonaCorporal).where(ZonaCorporal.nombre == "lumbar")
    )
    zona2 = await sesion.scalar(
        select(ZonaCorporal).where(ZonaCorporal.nombre == "isquiotibiales")
    )
    assert zona1 is not None and zona2 is not None

    fecha = date(2026, 8, 24)
    # 2 molestias en el dia + 1 de otro dia + 1 de otro usuario (no se puede
    # porque usuario_id es el unico seed, pero ordenamos por id).
    mol1 = Molestia(
        usuario_id=usuario_id,
        fecha=fecha,
        zona_id=zona2.id,
        intensidad=4,
    )
    mol2 = Molestia(
        usuario_id=usuario_id,
        fecha=fecha,
        zona_id=zona1.id,
        intensidad=2,
    )
    mol_otro_dia = Molestia(
        usuario_id=usuario_id,
        fecha=date(2026, 8, 23),
        zona_id=zona1.id,
        intensidad=3,
    )
    sesion.add_all([mol1, mol2, mol_otro_dia])
    await sesion.flush()

    resultado = await repo_molestia.listar_por_usuario_y_fecha(
        sesion, usuario_id, fecha
    )

    # Filtra por fecha exacta.
    assert len(resultado) == 2
    # Orden por id (mol1 insertado primero → id menor → primero en la lista).
    assert resultado[0].id == mol1.id
    assert resultado[1].id == mol2.id
    # Zona anidada via selectinload.
    assert resultado[0].zona is not None
    assert resultado[0].zona.nombre == "isquiotibiales"
    assert resultado[1].zona.nombre == "lumbar"


async def test_repositorio_molestias_por_usuario_y_fecha_vacio_si_no_hay(
    sesion: AsyncSession,
) -> None:
    """Sin filas para esa fecha: devuelve `[]`, no `None` ni error."""
    usuario_id, _ = await _ids_base(sesion)
    resultado = await repo_molestia.listar_por_usuario_y_fecha(
        sesion, usuario_id, date(2026, 8, 24)
    )
    assert resultado == []


# =================================================== R8.4 service =========


async def test_sesion_detalle_con_plan_shape_completo(
    sesion: AsyncSession,
) -> None:
    """`obtener_sesion_detalle` devuelve un `SesionDetalleRead` con todos
    los campos: cabecera, tipo_sesion, bloques (con ejercicio, objetivo y
    delta), bloques_no_ejecutados y molestias."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

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
        objetivo="fuerza full-body",
        duracion_min_est=50,
        rpe_objetivo=7,
        estado=EstadoSesionPlan.cumplido,
        nombre="Fuerza full-body",
        nota="nota del plan",
    )
    sesion.add(plan)
    await sesion.flush()

    bp1 = BloquePlan(
        sesion_plan_id=plan.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps_min=6,
        reps_max=8,
        peso_objetivo_kg=Decimal("80.0"),
    )
    bp2 = BloquePlan(
        sesion_plan_id=plan.id,
        ejercicio_id=ejercicio.id,
        orden=2,
        series=3,
        reps_min=8,
        reps_max=10,
        peso_objetivo_kg=Decimal("70.0"),
    )
    sesion.add_all([bp1, bp2])
    await sesion.flush()

    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
        fecha=date(2026, 8, 5),
        duracion_min=55,
        rpe=9,
        nota="buena sesion",
    )
    # Ejecuta solo el bloque 1: el 2 queda como no_ejecutado.
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=7,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("75.0"),
        rpe=9,
        dolor_lumbar=False,
    )

    # Molestia del mismo dia.
    zona = await sesion.scalar(
        select(ZonaCorporal).where(ZonaCorporal.nombre == "lumbar")
    )
    assert zona is not None
    sesion.add(
        Molestia(
            usuario_id=usuario_id,
            fecha=sesion_creada.fecha,
            zona_id=zona.id,
            intensidad=3,
        )
    )
    await sesion.flush()

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)

    # Cabecera.
    assert detalle.id == sesion_creada.id
    assert detalle.fecha == date(2026, 8, 5)
    assert detalle.tipo_sesion.id == tipo_sesion_id
    assert detalle.duracion_min == 55
    assert detalle.rpe == 9
    assert detalle.carga_srpe == 55 * 9
    assert detalle.nota == "buena sesion"

    # Plan.
    assert detalle.plan is not None
    assert detalle.plan.id == plan.id
    assert detalle.plan.nombre == "Fuerza full-body"
    assert detalle.plan.duracion_min_est == 50
    assert detalle.plan.rpe_objetivo == 7

    # Delta de sesion: duracion 55-50=5, rpe 9-7=2, carga 495-350=145.
    assert detalle.delta is not None
    assert detalle.delta.duracion_min == 5
    assert detalle.delta.rpe == 2
    assert detalle.delta.carga_srpe == 145

    # Bloques: solo el ejecutado (orden 1).
    assert len(detalle.bloques) == 1
    bloque_detalle = detalle.bloques[0]
    assert bloque_detalle.orden == 1
    assert bloque_detalle.ejercicio.id == ejercicio.id
    assert bloque_detalle.objetivo is not None
    assert bloque_detalle.objetivo.reps_min == 6
    assert bloque_detalle.objetivo.reps_max == 8
    # Delta bloque: series 0, reps 7 contra 6-8 → 0, peso 75-80=-5.
    assert bloque_detalle.delta.series == 0
    assert bloque_detalle.delta.reps == 0
    assert bloque_detalle.delta.peso_kg == Decimal("-5")

    # Bloques no ejecutados: orden 2.
    assert len(detalle.bloques_no_ejecutados) == 1
    no_ejecutado = detalle.bloques_no_ejecutados[0]
    assert no_ejecutado.orden == 2
    assert no_ejecutado.ejercicio_id == ejercicio.id
    assert no_ejecutado.objetivo.reps_min == 8
    assert no_ejecutado.objetivo.reps_max == 10

    # Molestia con zona anidada.
    assert len(detalle.molestias) == 1
    assert detalle.molestias[0].zona == "lumbar"
    assert detalle.molestias[0].intensidad == 3


async def test_sesion_detalle_libre_plan_null(
    sesion: AsyncSession,
) -> None:
    """Sesion sin plan: `plan=None`, `delta=None`, `bloques_no_ejecutados=[]`.
    El resto (cabecera, bloques, molestias) se llena normalmente."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)

    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=None,
        fecha=date(2026, 8, 24),
        duracion_min=45,
        rpe=6,
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=8,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("70.0"),
        rpe=None,
        dolor_lumbar=False,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)

    assert detalle.plan is None
    assert detalle.delta is None
    assert detalle.bloques_no_ejecutados == []
    # Bloque igual presente (aunque sin plan, el delta es todo NULL).
    assert len(detalle.bloques) == 1
    assert detalle.bloques[0].objetivo is None
    assert detalle.bloques[0].delta.series is None
    assert detalle.bloques[0].delta.reps is None


async def test_sesion_detalle_bloques_orden_asc(
    sesion: AsyncSession,
) -> None:
    """Los bloques vienen ordenados ascendente por `orden`, independientemente
    del orden en que se crearon."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)

    sesion_creada = await _crear_sesion_simple(
        sesion, usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id
    )
    for orden in (3, 1, 2):
        await repo.crear_bloque(
            sesion,
            sesion_id=sesion_creada.id,
            ejercicio_id=ejercicio.id,
            orden=orden,
            series=3,
            reps=8,
            distancia_m=None,
            duracion_s=None,
            calidad=None,
            peso_kg=Decimal("80.0"),
            rpe=None,
            dolor_lumbar=False,
        )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)

    assert [b.orden for b in detalle.bloques] == [1, 2, 3]


async def test_sesion_detalle_bloques_no_ejecutados(
    sesion: AsyncSession,
) -> None:
    """Plan con 5 bloques_planeados, sesion ejecuta 3 → bloques_no_ejecutados
    tiene 2 con los ordenes que faltan, ordenados por su propio orden."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)

    plan = SesionPlan(
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        objetivo="5 bloques",
        duracion_min_est=60,
        rpe_objetivo=7,
        estado=EstadoSesionPlan.movido,
    )
    sesion.add(plan)
    await sesion.flush()
    for orden in range(1, 6):
        sesion.add(
            BloquePlan(
                sesion_plan_id=plan.id,
                ejercicio_id=ejercicio.id,
                orden=orden,
                series=3,
                reps_min=8,
                reps_max=10,
                peso_objetivo_kg=Decimal("80.0"),
            )
        )
    await sesion.flush()

    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
    )
    # Solo ejecuta los ordenes 1, 3, 5.
    for orden in (1, 3, 5):
        await repo.crear_bloque(
            sesion,
            sesion_id=sesion_creada.id,
            ejercicio_id=ejercicio.id,
            orden=orden,
            series=3,
            reps=8,
            distancia_m=None,
            duracion_s=None,
            calidad=None,
            peso_kg=Decimal("80.0"),
            rpe=None,
            dolor_lumbar=False,
        )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)

    ordenes_no_ejecutados = [b.orden for b in detalle.bloques_no_ejecutados]
    assert ordenes_no_ejecutados == [2, 4]


async def test_sesion_detalle_molestias_zona_anidada(
    sesion: AsyncSession,
) -> None:
    """Las molestias devueltas tienen `zona` (string con el nombre) y
    `intensidad`. Sin `zona_id` (la API pública expone el nombre, no el id)."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    sesion_creada = await _crear_sesion_simple(
        sesion, usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id
    )

    zona_lumbar = await sesion.scalar(
        select(ZonaCorporal).where(ZonaCorporal.nombre == "lumbar")
    )
    zona_isquio = await sesion.scalar(
        select(ZonaCorporal).where(ZonaCorporal.nombre == "isquiotibiales")
    )
    assert zona_lumbar is not None and zona_isquio is not None
    sesion.add_all(
        [
            Molestia(
                usuario_id=usuario_id,
                fecha=sesion_creada.fecha,
                zona_id=zona_isquio.id,
                intensidad=5,
            ),
            Molestia(
                usuario_id=usuario_id,
                fecha=sesion_creada.fecha,
                zona_id=zona_lumbar.id,
                intensidad=2,
            ),
        ]
    )
    await sesion.flush()

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)

    assert len(detalle.molestias) == 2
    # Orden por id (orden de insercion en este caso): isquio primero.
    assert detalle.molestias[0].zona == "isquiotibiales"
    assert detalle.molestias[0].intensidad == 5
    assert detalle.molestias[1].zona == "lumbar"
    assert detalle.molestias[1].intensidad == 2


async def test_sesion_detalle_delta_bloque_peso_negativo(
    sesion: AsyncSession,
) -> None:
    """Bloque ejecutado: 3x8@80 contra plan 3x8@90 → delta.peso=-10."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)
    plan = SesionPlan(
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        duracion_min_est=50,
        rpe_objetivo=7,
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
            reps_max=8,
            peso_objetivo_kg=Decimal("90.0"),
        )
    )
    await sesion.flush()
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=8,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("80.0"),
        rpe=None,
        dolor_lumbar=False,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.bloques[0].delta.peso_kg == Decimal("-10")


async def test_sesion_detalle_delta_bloque_dentro_rango(
    sesion: AsyncSession,
) -> None:
    """7 reps contra rango 6-8 → delta.reps=0 (dentro del rango)."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)
    plan = SesionPlan(
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
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
        )
    )
    await sesion.flush()
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=7,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=None,
        rpe=None,
        dolor_lumbar=False,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.bloques[0].delta.reps == 0


async def test_sesion_detalle_delta_bloque_sobre_rango(
    sesion: AsyncSession,
) -> None:
    """10 reps contra rango 6-8 → delta.reps=+2 (10-8)."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)
    plan = SesionPlan(usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id)
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
        )
    )
    await sesion.flush()
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=10,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=None,
        rpe=None,
        dolor_lumbar=False,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.bloques[0].delta.reps == 2


async def test_sesion_detalle_delta_bloque_objetivo_nulo(
    sesion: AsyncSession,
) -> None:
    """Plan con todos los campos objetivo NULL → todas las keys del delta
    son NULL."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)
    plan = SesionPlan(usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id)
    sesion.add(plan)
    await sesion.flush()
    sesion.add(
        BloquePlan(
            sesion_plan_id=plan.id,
            ejercicio_id=ejercicio.id,
            orden=1,
            series=None,
            reps_min=None,
            reps_max=None,
            peso_objetivo_kg=None,
        )
    )
    await sesion.flush()
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=8,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("80.0"),
        rpe=None,
        dolor_lumbar=False,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.bloques[0].delta.series is None
    assert detalle.bloques[0].delta.reps is None
    assert detalle.bloques[0].delta.peso_kg is None


async def test_sesion_detalle_delta_bloque_sin_plan(
    sesion: AsyncSession,
) -> None:
    """Bloque sin bloque_plan (sesion libre): `objetivo=None` y todas las
    keys del delta son NULL."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    ejercicio = await _ejercicio_de_medicion(sesion, TipoMedicion.carga)
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=None,
    )
    await repo.crear_bloque(
        sesion,
        sesion_id=sesion_creada.id,
        ejercicio_id=ejercicio.id,
        orden=1,
        series=3,
        reps=8,
        distancia_m=None,
        duracion_s=None,
        calidad=None,
        peso_kg=Decimal("80.0"),
        rpe=None,
        dolor_lumbar=False,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.bloques[0].objetivo is None
    assert detalle.bloques[0].delta.series is None
    assert detalle.bloques[0].delta.reps is None
    assert detalle.bloques[0].delta.peso_kg is None
    assert detalle.bloques[0].delta.distancia_m is None
    assert detalle.bloques[0].delta.duracion_s is None


async def test_sesion_detalle_delta_sesion_duracion(
    sesion: AsyncSession,
) -> None:
    """55 min reales contra 50 min estimados → delta.duracion_min=+5."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    plan = SesionPlan(
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        duracion_min_est=50,
        rpe_objetivo=7,
    )
    sesion.add(plan)
    await sesion.flush()
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
        duracion_min=55,
        rpe=7,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.delta is not None
    assert detalle.delta.duracion_min == 5


async def test_sesion_detalle_delta_sesion_rpe(
    sesion: AsyncSession,
) -> None:
    """rpe real 9 contra rpe_objetivo 7 → delta.rpe=+2."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    plan = SesionPlan(
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        duracion_min_est=55,
        rpe_objetivo=7,
    )
    sesion.add(plan)
    await sesion.flush()
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
        duracion_min=55,
        rpe=9,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.delta is not None
    assert detalle.delta.rpe == 2


async def test_sesion_detalle_delta_sesion_carga(
    sesion: AsyncSession,
) -> None:
    """carga_srpe real 495 contra objetivo 55*7=385 → delta.carga_srpe=+110.
    El delta de carga es contra la multiplicacion de los 2 parametros del
    plan, no contra un campo directo."""
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    plan = SesionPlan(
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        duracion_min_est=55,
        rpe_objetivo=7,
    )
    sesion.add(plan)
    await sesion.flush()
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
        duracion_min=55,
        rpe=9,
    )

    detalle = await obtener_sesion_detalle(sesion, sesion_creada.id)
    assert detalle.delta is not None
    assert detalle.delta.carga_srpe == 110


async def test_sesion_detalle_404_si_no_existe(sesion: AsyncSession) -> None:
    """`obtener_sesion_detalle` levanta `RecursoNoEncontradoError` si la
    sesion no existe (UUID valido pero sin fila)."""
    from app.core.exceptions import RecursoNoEncontradoError
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    with pytest.raises(RecursoNoEncontradoError):
        await obtener_sesion_detalle(sesion, uuid.uuid4())


async def test_sesion_detalle_404_si_no_es_del_usuario(
    sesion: AsyncSession,
) -> None:
    """Aunque la sesion exista, si pertenece a otro usuario: 404 (no se
    filtra la existencia, AGENTS §5)."""
    from app.core.exceptions import RecursoNoEncontradoError
    from app.services.entrenamiento.sesion import obtener_sesion_detalle

    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    sesion_creada = await _crear_sesion_simple(
        sesion, usuario_id=usuario_id, tipo_sesion_id=tipo_sesion_id
    )
    otro_usuario_id = uuid.uuid4()

    with pytest.raises(RecursoNoEncontradoError):
        await obtener_sesion_detalle(
            sesion, sesion_creada.id, usuario_id=otro_usuario_id
        )


# =================================================== R8.5 router =========


async def test_router_get_sesion_detalle_devuelve_sesion_detalle_read(
    sesion: AsyncSession,
    cliente: AsyncClient,
) -> None:
    """`GET /sesiones/{id}` devuelve un `SesionDetalleRead` con `plan` y
    `bloques` anidados (no el `SesionRead` plano)."""
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        duracion_min=50,
        rpe=7,
    )

    respuesta = await cliente.get(f"/api/v1/sesiones/{sesion_creada.id}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == str(sesion_creada.id)
    assert cuerpo["tipo_sesion"]["codigo"] == "fuerza"
    assert cuerpo["carga_srpe"] == 50 * 7
    assert "bloques" in cuerpo
    assert "bloques_no_ejecutados" in cuerpo
    assert "molestias" in cuerpo
    assert cuerpo["plan"] is None
    assert cuerpo["delta"] is None


async def test_router_get_sesion_detalle_404_si_no_existe(
    cliente: AsyncClient,
) -> None:
    respuesta = await cliente.get(f"/api/v1/sesiones/{uuid.uuid4()}")
    assert respuesta.status_code == 404


async def test_router_get_sesion_detalle_401_sin_token() -> None:
    """Sin Authorization: 401 (la dependencia get_usuario_actual rechaza)."""
    from httpx import ASGITransport

    from app.main import app as _app

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as sin_auth:
        respuesta = await sin_auth.get(f"/api/v1/sesiones/{uuid.uuid4()}")
    assert respuesta.status_code == 401


# =================================================== R8.6 regresion N+1 ====


@pytest.fixture
async def contador_queries(
    sesion: AsyncSession,
) -> AsyncGenerator[dict[str, int], None]:
    """Cuenta queries ejecutadas durante el test. Filtra SAVEPOINTs y
    queries internas de Postgres (SET, BEGIN, etc.) para que solo se
    cuenten las queries de la aplicacion."""
    engine = sesion.bind  # AsyncEngine
    sync_engine = engine.sync_engine
    contador: dict[str, int] = {"n": 0}

    def contar(conn, cursor, statement, parameters, context, executemany) -> None:
        # Filtrar SAVEPOINTs y transacciones de control.
        stmt = statement.strip().upper()
        if not stmt:
            return
        primera = stmt.split(maxsplit=1)[0]
        if primera in {
            "BEGIN",
            "COMMIT",
            "ROLLBACK",
            "SAVEPOINT",
            "RELEASE",
            "SET",
            "SHOW",
            "SELECT",  # pg internal selects
        }:
            # Los `SELECT 1` los mete Postgres en algunos paths; los
            # filtramos tambien para que el umbral refleje solo las
            # queries reales de la app.
            if stmt.startswith("SELECT 1"):
                return
            if stmt.startswith("SELECT PG_"):
                return
        # Aceptamos SELECT/UPDATE/INSERT/DELETE explicitos de la app.
        if primera in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
            contador["n"] += 1

    event.listen(sync_engine, "before_cursor_execute", contar)
    try:
        yield contador
    finally:
        event.remove(sync_engine, "before_cursor_execute", contar)


async def test_sesion_detalle_no_supera_9_queries(
    sesion: AsyncSession,
    cliente: AsyncClient,
    contador_queries: dict[str, int],
) -> None:
    """Regresion N+1: el detalle de sesion con plan + bloques + bloques
    planeados + ciclo + molestias no dispara mas de 9 queries.

    Punto de partida teorico con `joinedload` + `selectinload`:
    1. Sesion + tipo_sesion + sesion_plan (joinedload, 1 query)
    2. bloques (selectinload, 1 query batch)
    3. ejercicios de bloques (selectinload anidado, 1 query batch)
    4. bloques_planeados (selectinload anidado al plan, 1 query)
    5. ejercicios de bloques_planeados (selectinload anidado, 1 query)
    6. ciclo_semana (selectinload, 1 query)
    7. ciclo (selectinload anidado al ciclo_semana, 1 query)
    8. molestias del dia (1 query)
    9. zonas de las molestias (selectinload, 1 query)

    9 SELECTs totales, todos con batch-loading. Cualquier suba por encima
    seria un N+1 nuevo (acceso por fila en vez de por coleccion).

    NOTA: el plan original proponia 8. La combinacion de las 4 colecciones
    (bloques, bloques_planeados, ciclo_semana+ciclo, molestias+zonas) mas
    la query principal + tipo_sesion + sesion_plan llega a 9 sin N+1: cada
    nivel de coleccion es una query batcheada propia. Combinar
    `bloques.ejercicio` con `bloques_planeados.ejercicio` exigiria un JOIN
    o subquery manual sobre la misma tabla `ejercicio` (lo que el patron
    `selectinload` anidado ya hace por separado sin riesgo de
    duplicacion). AGENTS §3.1 prohibe desnormalizar para bajar el
    conteo."""
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
        estado=EstadoSesionPlan.cumplido,
    )
    sesion.add(plan)
    await sesion.flush()
    for orden in range(1, 4):
        sesion.add(
            BloquePlan(
                sesion_plan_id=plan.id,
                ejercicio_id=ejercicio.id,
                orden=orden,
                series=3,
                reps_min=6,
                reps_max=8,
                peso_objetivo_kg=Decimal("80.0"),
            )
        )
    await sesion.flush()

    sesion_creada = await _crear_sesion_simple(
        sesion,
        usuario_id=usuario_id,
        tipo_sesion_id=tipo_sesion_id,
        sesion_plan_id=plan.id,
        fecha=date(2026, 8, 5),
        duracion_min=55,
        rpe=9,
    )
    for orden in (1, 2):
        await repo.crear_bloque(
            sesion,
            sesion_id=sesion_creada.id,
            ejercicio_id=ejercicio.id,
            orden=orden,
            series=3,
            reps=8,
            distancia_m=None,
            duracion_s=None,
            calidad=None,
            peso_kg=Decimal("80.0"),
            rpe=None,
            dolor_lumbar=False,
        )

    # Una molestia del dia: agrega 1 query (selectinload de zona).
    zona = await sesion.scalar(
        select(ZonaCorporal).where(ZonaCorporal.nombre == "lumbar")
    )
    assert zona is not None
    sesion.add(
        Molestia(
            usuario_id=usuario_id,
            fecha=sesion_creada.fecha,
            zona_id=zona.id,
            intensidad=3,
        )
    )
    await sesion.flush()

    contador_queries["n"] = 0
    respuesta = await cliente.get(f"/api/v1/sesiones/{sesion_creada.id}")
    assert respuesta.status_code == 200
    assert contador_queries["n"] <= 9, (
        f"detalle de sesion hizo {contador_queries['n']} queries; el umbral es 9"
    )
