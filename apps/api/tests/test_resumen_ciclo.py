"""Resumen de ciclo (REGLAS_NEGOCIO §17) y los exports `perfil` / `resumen_ciclo`.

Escenario fijo: ciclo 9 activo desde el lunes 2026-09-21; "hoy" es el jueves
2026-10-01 (semana 2 en curso). Los numeros esperados salen de los casos de §17.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.core.exceptions import RecursoNoEncontradoError
from app.db.session import get_session
from app.main import app
from app.models import (
    Ciclo,
    CicloSemana,
    Habito,
    HabitoRegistro,
    MedidaCorporal,
    RegistroHidratacion,
    RegistroSueno,
    Sesion,
    SesionPlan,
    TestFisico,
    TestIntento,
    TipoSesion,
    TipoTest,
    Usuario,
)
from app.models.enums import EstadoCiclo, EstadoSesionPlan, FaseCiclo
from app.schemas.metricas.resumen_ciclo import ResumenCicloRead
from app.services.entrenamiento.importacion import construir_export
from app.services.metricas.resumen_ciclo import construir_resumen_ciclo

INICIO = date(2026, 9, 21)  # lunes
HOY = date(2026, 10, 1)  # jueves de la semana 2


@pytest.fixture
async def usuario(sesion: AsyncSession) -> Usuario:
    u = await sesion.scalar(select(Usuario))
    assert u is not None
    return u


@pytest.fixture
async def cliente(
    sesion: AsyncSession, usuario: Usuario
) -> AsyncGenerator[AsyncClient, None]:
    async def _sesion() -> AsyncGenerator[AsyncSession, None]:
        yield sesion

    app.dependency_overrides[get_session] = _sesion
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


async def _plan(
    sesion: AsyncSession,
    usuario: Usuario,
    semana: CicloSemana,
    tipo: str,
    dia: int,
    estado: EstadoSesionPlan,
    rpe: int | None,
    duracion: int | None,
) -> SesionPlan:
    plan = SesionPlan(
        usuario_id=usuario.id,
        ciclo_semana_id=semana.id,
        dia_sugerido=dia,
        tipo_sesion_id=await _tipo(sesion, tipo),
        estado=estado,
        rpe_objetivo=rpe,
        duracion_min_est=duracion,
        clave_import=f"{dia}-{tipo}",
    )
    sesion.add(plan)
    await sesion.flush()
    return plan


async def _real(
    sesion: AsyncSession,
    usuario: Usuario,
    tipo: str,
    fecha: date,
    rpe: int,
    duracion: int,
    plan: SesionPlan | None = None,
) -> Sesion:
    s = Sesion(
        usuario_id=usuario.id,
        sesion_plan_id=plan.id if plan else None,
        fecha=fecha,
        tipo_sesion_id=await _tipo(sesion, tipo),
        duracion_min=duracion,
        rpe=rpe,
        idempotency_key=uuid.uuid4(),
    )
    sesion.add(s)
    await sesion.flush()
    return s


async def _ciclo(
    sesion: AsyncSession,
    usuario: Usuario,
    *,
    numero: int = 9,
    estado: EstadoCiclo = EstadoCiclo.activo,
    inicio: date = INICIO,
    cierre: date | None = None,
) -> Ciclo:
    c = Ciclo(
        usuario_id=usuario.id,
        numero=numero,
        objetivo=f"Ciclo {numero}",
        fecha_inicio=inicio,
        semanas=4,
        estado=estado,
        fecha_cierre_real=cierre,
    )
    sesion.add(c)
    await sesion.flush()
    await sesion.refresh(c)
    return c


async def _escenario(sesion: AsyncSession, usuario: Usuario) -> Ciclo:
    ciclo = await _ciclo(sesion, usuario)
    semanas = []
    for numero, fase in (
        (1, FaseCiclo.readaptacion),
        (2, FaseCiclo.carga),
        (3, FaseCiclo.carga),
    ):
        s = CicloSemana(
            ciclo_id=ciclo.id,
            numero=numero,
            fase=fase,
            rpe_objetivo_min=5,
            rpe_objetivo_max=6,
            volumen_pct=65,
        )
        sesion.add(s)
        semanas.append(s)
    await sesion.flush()
    s1, s2, _s3 = semanas
    est = EstadoSesionPlan

    # Semana 1: 4 planes -> 1 cumplido, 1 movido, 1 descartado, 1 pendiente.
    a = await _plan(sesion, usuario, s1, "fuerza", 0, est.cumplido, 6, 60)
    b = await _plan(sesion, usuario, s1, "velocidad_salto", 2, est.movido, 8, 90)
    await _plan(sesion, usuario, s1, "resistencia", 4, est.descartado, 5, 40)
    await _plan(sesion, usuario, s1, "balon_control", 5, est.pendiente, None, 45)
    await _real(sesion, usuario, "fuerza", date(2026, 9, 21), 7, 70, a)
    await _real(sesion, usuario, "velocidad_salto", date(2026, 9, 24), 8, 80, b)
    await _real(sesion, usuario, "recuperacion", date(2026, 9, 26), 5, 40)  # libre

    # Semana 2 (en curso): un cumplido y un pendiente.
    e = await _plan(sesion, usuario, s2, "fuerza", 0, est.cumplido, 7, 60)
    await _plan(sesion, usuario, s2, "partido", 2, est.pendiente, 8, 90)
    await _real(sesion, usuario, "fuerza", date(2026, 9, 28), 7, 60, e)

    # Sueno: 7 h y 8 h en la semana 1.
    for dia, horas in ((date(2026, 9, 22), 7), (date(2026, 9, 23), 8)):
        fin = datetime(dia.year, dia.month, dia.day, 6, tzinfo=UTC)
        sesion.add(
            RegistroSueno(
                usuario_id=usuario.id,
                fecha=dia,
                inicio=fin - timedelta(hours=horas),
                fin=fin,
            )
        )
    for dia, ml in ((date(2026, 9, 22), 2500), (date(2026, 9, 23), 3500)):
        sesion.add(RegistroHidratacion(usuario_id=usuario.id, fecha=dia, ml_totales=ml))

    # Habito marcado 5 de 7 dias en la semana 1.
    creatina = await sesion.scalar(select(Habito).where(Habito.nombre == "creatina"))
    assert creatina is not None
    for k in range(5):
        sesion.add(
            HabitoRegistro(
                habito_id=creatina.id, fecha=INICIO + timedelta(days=k), valor=True
            )
        )

    sesion.add(
        MedidaCorporal(
            usuario_id=usuario.id,
            fecha=INICIO,
            peso_kg=Decimal("80.00"),
            cintura_cm=Decimal("90.0"),
        )
    )
    sesion.add(
        MedidaCorporal(
            usuario_id=usuario.id,
            fecha=date(2026, 9, 28),
            peso_kg=Decimal("79.00"),
            cintura_cm=Decimal("88.5"),
        )
    )

    # CMJ: base historica (antes del ciclo) y un test dentro del ciclo.
    cmj = await sesion.scalar(select(TipoTest).where(TipoTest.codigo == "cmj"))
    assert cmj is not None
    for fecha, valores in ((date(2026, 9, 1), (40, 41)), (date(2026, 9, 28), (43,))):
        t = TestFisico(
            usuario_id=usuario.id,
            fecha=fecha,
            tipo_test_id=cmj.id,
            idempotency_key=uuid.uuid4(),
        )
        sesion.add(t)
        await sesion.flush()
        for n, v in enumerate(valores, start=1):
            sesion.add(TestIntento(test_fisico_id=t.id, numero=n, valor=Decimal(v)))
    await sesion.flush()
    return ciclo


async def test_resumen_cumplimiento_por_estado(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _escenario(sesion, usuario)
    r = await construir_resumen_ciclo(sesion, usuario.id, HOY)

    assert r.ciclo.numero == 9
    assert r.ciclo.informado_hasta == HOY
    # La semana 3 empieza el 5/10: es futura y no se informa.
    assert [s.numero for s in r.semanas] == [1, 2]
    assert [s.estado for s in r.semanas] == ["completa", "en_curso"]

    c = r.semanas[0].cumplimiento
    assert (c.planeadas, c.cumplido, c.movido, c.descartado, c.pendiente) == (
        4,
        1,
        1,
        1,
        1,
    )
    assert c.sesiones_sin_plan == 1
    assert c.pct_ejecutado == 66.7  # 2 / (4 - 1)

    # Totales: sem 1 (4 planes) + sem 2 (2 planes: 1 cumplido, 1 pendiente).
    t = r.totales.cumplimiento
    assert (t.planeadas, t.cumplido, t.movido, t.pendiente) == (6, 2, 1, 2)
    assert t.pct_ejecutado == 60.0  # (2 + 1) / (6 - 1)


async def test_resumen_planeado_vs_real_y_carga(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _escenario(sesion, usuario)
    s1 = (await construir_resumen_ciclo(sesion, usuario.id, HOY)).semanas[0]

    pvr = s1.planeado_vs_real
    assert pvr.pares == 2
    assert pvr.rpe_planeado_prom == 7.0  # (6 + 8) / 2
    assert pvr.rpe_real_prom == 7.5  # (7 + 8) / 2
    assert pvr.duracion_planeada_min == 150
    assert pvr.duracion_real_min == 150  # 70 + 80

    # Planeada: 6x60 + 8x90 + 5x40 (el pendiente sin rpe no aporta) = 1280.
    assert s1.carga.planeada == 1280
    # Real: 7x70 + 8x80 + 5x40 (la sesion libre cuenta) = 1330.
    assert s1.carga.real == 1330

    libres = [f for f in s1.sesiones if f.estado_plan is None]
    assert [(f.tipo, f.carga_srpe) for f in libres] == [("recuperacion", 200)]
    pendiente = next(f for f in s1.sesiones if f.estado_plan == "pendiente")
    assert pendiente.carga_srpe is None and pendiente.fecha_real is None


async def test_resumen_sueno_agua_habitos_y_medidas(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _escenario(sesion, usuario)
    r = await construir_resumen_ciclo(sesion, usuario.id, HOY)
    s1, s2 = r.semanas

    assert s1.sueno_horas.promedio == 7.5
    assert s1.sueno_horas.dias_con_dato == 2
    assert s1.sueno_horas.objetivo == 7.0
    assert s1.agua_ml.promedio == 3000.0
    # Sin registros: NULL, no 0 (§14).
    assert s2.sueno_horas.promedio is None
    assert s2.sueno_horas.dias_con_dato == 0

    creatina = next(h for h in s1.habitos if h.nombre == "creatina")
    assert (creatina.dias_cumplidos, creatina.dias_transcurridos) == (5, 7)
    assert creatina.pct_cumplimiento == 71.4
    # Semana en curso: solo cuentan los dias hasta hoy (lun 28 a jue 1 = 4).
    assert s2.habitos[0].dias_transcurridos == 4

    assert [m.peso_kg for m in s1.medidas] == [80.0]
    cambio = r.cambio_corporal
    assert cambio is not None
    assert (cambio.peso_inicial_kg, cambio.peso_final_kg) == (80.0, 79.0)
    assert cambio.cambio_peso_kg == -1.0
    assert cambio.cambio_cintura_cm == -1.5


async def test_resumen_pruebas_usa_la_base_historica(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _escenario(sesion, usuario)
    r = await construir_resumen_ciclo(sesion, usuario.id, HOY)

    assert [p.codigo for p in r.pruebas] == ["cmj"]
    cmj = r.pruebas[0]
    assert cmj.base_fecha == date(2026, 9, 1)
    assert cmj.base_mejor == 41.0  # mejor del primer test historico
    assert len(cmj.resultados) == 1  # el de septiembre 1 es previo al ciclo
    assert cmj.resultados[0].mejor == 43.0
    assert cmj.resultados[0].pct_cambio_vs_base == 4.878  # §8: 100 x (43-41)/41


async def test_sin_ciclo_activo_ni_cerrado_es_404(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _ciclo(sesion, usuario, estado=EstadoCiclo.planificado)
    with pytest.raises(RecursoNoEncontradoError):
        await construir_resumen_ciclo(sesion, usuario.id, HOY)


async def test_sin_activo_usa_el_ultimo_cerrado(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _ciclo(
        sesion,
        usuario,
        numero=1,
        estado=EstadoCiclo.cerrado,
        inicio=date(2026, 6, 1),
        cierre=date(2026, 6, 28),
    )
    await _ciclo(
        sesion,
        usuario,
        numero=2,
        estado=EstadoCiclo.cerrado,
        inicio=date(2026, 7, 6),
        cierre=date(2026, 8, 2),
    )
    r = await construir_resumen_ciclo(sesion, usuario.id, HOY)
    assert r.ciclo.numero == 2
    # Un ciclo terminado se informa hasta su cierre, no hasta hoy.
    assert r.ciclo.informado_hasta == date(2026, 8, 2)


async def test_el_activo_gana_sobre_un_cerrado_mas_nuevo(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _ciclo(sesion, usuario, numero=1)
    await _ciclo(
        sesion,
        usuario,
        numero=5,
        estado=EstadoCiclo.cerrado,
        inicio=date(2026, 6, 1),
        cierre=date(2026, 6, 28),
    )
    assert (await construir_resumen_ciclo(sesion, usuario.id, HOY)).ciclo.numero == 1


# ------------------------------------------------------------------ exports --


async def test_export_resumen_ciclo_es_json_numerico(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _escenario(sesion, usuario)
    export = await construir_export(sesion, "resumen_ciclo", usuario.id)
    assert export.formato == "json"
    datos = json.loads(export.contenido)
    # Numeros como numeros, no como strings: el consumidor es un LLM.
    assert datos["semanas"][0]["sueno_horas"]["promedio"] == 7.5
    assert datos["pruebas"][0]["resultados"][0]["mejor"] == 43.0


async def test_export_resumen_ciclo_sin_ciclo_devuelve_404(
    cliente: AsyncClient,
) -> None:
    r = await cliente.get("/api/v1/planes/importar/export/resumen_ciclo")
    assert r.status_code == 404


async def test_export_perfil_incluye_el_perfil_y_la_ultima_medida(
    cliente: AsyncClient, sesion: AsyncSession, usuario: Usuario
) -> None:
    sesion.add(
        MedidaCorporal(
            usuario_id=usuario.id,
            fecha=date(2026, 9, 28),
            peso_kg=Decimal("79.50"),
            cintura_cm=Decimal("88.5"),
        )
    )
    await sesion.flush()
    r = await cliente.get("/api/v1/planes/importar/export/perfil")
    assert r.status_code == 200
    assert r.json()["formato"] == "json"
    perfil = json.loads(r.json()["contenido"])
    assert perfil["posicion"] == "Extremo izquierdo"
    assert perfil["talla_cm"] == 178.0
    assert perfil["peso_kg"] == 80.0  # declarado
    assert perfil["ultima_medida"] == {
        "fecha": "2026-09-28",
        "peso_kg": 79.5,
        "cintura_cm": 88.5,
    }
    assert perfil["ventanas"][0]["lugares"] == ["Gimnasio"]
    assert len(perfil["eventos_fijos"]) == 2


async def test_la_plantilla_reglas_solo_nombra_campos_que_existen() -> None:
    """Si alguien renombra un campo del resumen, la plantilla que le explica el
    JSON al LLM no puede quedar describiendo algo que ya no existe."""
    import importlib.resources

    plantilla = (
        importlib.resources.files("app.resources")
        .joinpath("reglas-import.md")
        .read_text("utf-8")
    )
    seccion = plantilla[plantilla.index("## 10. Planear a partir") :]

    def propiedades(esquema: dict) -> set[str]:  # type: ignore[type-arg]
        nombres: set[str] = set()

        def recorrer(nodo: object) -> None:
            if isinstance(nodo, dict):
                nombres.update(nodo.get("properties", {}))
                for v in nodo.values():
                    recorrer(v)
            elif isinstance(nodo, list):
                for v in nodo:
                    recorrer(v)

        recorrer(esquema)
        return nombres

    campos = propiedades(ResumenCicloRead.model_json_schema())
    for nombre in (
        "informado_hasta",
        "pct_ejecutado",
        "pendiente",
        "descartado",
        "planeado_vs_real",
        "carga",
        "pct_cambio_vs_base",
        "sueno_horas",
        "agua_ml",
        "habitos",
        "objetivo",
        "dias_con_dato",
        "dias_con_registro",
        "cambio_corporal",
    ):
        assert f"`{nombre}`" in seccion or nombre in seccion, nombre
        assert nombre in campos, nombre
