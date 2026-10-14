"""Las cuatro preguntas de Progreso (REGLAS_NEGOCIO §18)."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.main import app
from app.models import (
    Bloque,
    Ejercicio,
    MedidaCorporal,
    RegistroSueno,
    Sesion,
    TipoSesion,
    Usuario,
)
from app.models.enums import TipoMedicion
from app.schemas.metricas.progreso import SemanaComposicion
from app.services.metricas import conclusiones, progreso
from tests.test_resumen_ciclo import HOY, _escenario


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


async def _sesion_con_carga(
    sesion: AsyncSession, usuario: Usuario, fecha: date, rpe: int, minutos: int
) -> Sesion:
    tipo = await sesion.scalar(
        select(TipoSesion.id).where(TipoSesion.codigo == "fuerza")
    )
    assert tipo is not None
    s = Sesion(
        usuario_id=usuario.id,
        fecha=fecha,
        tipo_sesion_id=tipo,
        duracion_min=minutos,
        rpe=rpe,
        idempotency_key=uuid.uuid4(),
    )
    sesion.add(s)
    await sesion.flush()
    return s


# ------------------------------------------------------ 1. ¿Cumpli el plan? --


async def test_cumplimiento_reparte_los_cuatro_estados_sobre_el_total(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _escenario(sesion, usuario)
    r = await progreso.cumplimiento(sesion, usuario.id, HOY)

    assert r.ciclo_numero == 9
    assert [s.numero for s in r.semanas] == [1, 2]
    s1 = r.semanas[0]
    # 4 planes: 1 cumplido, 1 movido, 1 descartado, 1 pendiente -> 25 % cada uno.
    assert (s1.pct_cumplido, s1.pct_movido, s1.pct_descartado, s1.pct_pendiente) == (
        25.0,
        25.0,
        25.0,
        25.0,
    )
    s2 = r.semanas[1]
    assert (s2.planeadas, s2.pct_cumplido, s2.pct_pendiente) == (2, 50.0, 50.0)
    assert r.conclusion.startswith("En la semana 2 ejecutaste 1 de 2 sesiones")


async def test_cumplimiento_sin_ciclo_responde_vacio_no_error(
    cliente: AsyncClient,
) -> None:
    r = await cliente.get("/api/v1/progreso/cumplimiento")
    assert r.status_code == 200
    assert r.json()["semanas"] == []
    assert r.json()["ciclo_numero"] is None


# ------------------------------------------------ 2. ¿Estoy rindiendo mejor? --


async def _ejercicio(sesion: AsyncSession, tipo: TipoMedicion) -> Ejercicio:
    e = await sesion.scalar(select(Ejercicio).where(Ejercicio.tipo_medicion == tipo))
    assert e is not None
    return e


async def test_mejor_marca_de_carga_da_peso_maximo_y_1rm_de_epley(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    ejercicio = await _ejercicio(sesion, TipoMedicion.carga)
    s = await _sesion_con_carga(sesion, usuario, date(2026, 9, 28), 7, 60)
    # (peso, reps): el de 120 x 12 tiene mas peso pero supera epley_reps_max.
    for orden, (peso, reps) in enumerate([(100, 5), (110, 3), (120, 12)], start=1):
        sesion.add(
            Bloque(
                sesion_id=s.id,
                ejercicio_id=ejercicio.id,
                orden=orden,
                series=3,
                reps=reps,
                peso_kg=Decimal(peso),
            )
        )
    await sesion.flush()

    r = await progreso.rendimiento(sesion, usuario.id, HOY)
    marca = next(m for m in r.marcas if m.ejercicio_id == ejercicio.id)
    assert marca.tipo_medicion == "carga"
    assert marca.peso_max_kg == 120.0
    # 110 x (1 + 3/30) = 121.0 gana a 100 x (1 + 5/30) = 116.7; el de 12 reps no cuenta.
    assert marca.rm_estimado_kg == 121.0
    assert marca.fecha == date(2026, 9, 28)


async def test_mejor_marca_de_tiempo_es_la_mayor_duracion(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    ejercicio = await _ejercicio(sesion, TipoMedicion.tiempo)
    for fecha, seg in ((date(2026, 9, 21), 30), (date(2026, 9, 28), 45)):
        s = await _sesion_con_carga(sesion, usuario, fecha, 6, 40)
        sesion.add(
            Bloque(sesion_id=s.id, ejercicio_id=ejercicio.id, orden=1, duracion_s=seg)
        )
    await sesion.flush()

    r = await progreso.rendimiento(sesion, usuario.id, HOY)
    marca = next(m for m in r.marcas if m.ejercicio_id == ejercicio.id)
    assert marca.duracion_max_s == 45
    assert marca.peso_max_kg is None
    assert marca.fecha == date(2026, 9, 28)


async def test_tendencia_de_pruebas_compara_contra_la_primera(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    await _escenario(sesion, usuario)  # CMJ: base 41 el 1/9, 43 el 28/9
    r = await progreso.rendimiento(sesion, usuario.id, HOY)
    cmj = next(p for p in r.pruebas if p.codigo == "cmj")
    assert [(p.fecha, p.mejor) for p in cmj.puntos] == [
        (date(2026, 9, 1), 41.0),
        (date(2026, 9, 28), 43.0),
    ]
    assert cmj.puntos[0].pct_cambio_vs_base is None
    assert cmj.puntos[1].pct_cambio_vs_base == 4.878
    assert r.conclusion.startswith(
        "Pruebas mejor que en la primera medición: 1 de 1 (Salto CMJ)"
    )


# ------------------------------------------------- 3. ¿Me estoy recuperando? --

DOMINGO = date(2026, 10, 11)


async def test_recuperacion_calcula_acwr_semaforo_y_sueno_por_semana(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    # Caso 2000 / 7400 de REGLAS §3: 5400 hace 27 dias y 2000 hoy.
    await _sesion_con_carga(sesion, usuario, DOMINGO - timedelta(days=27), 9, 600)
    await _sesion_con_carga(sesion, usuario, DOMINGO, 10, 200)
    fin = datetime(2026, 10, 7, 6, tzinfo=UTC)
    sesion.add(
        RegistroSueno(
            usuario_id=usuario.id,
            fecha=date(2026, 10, 7),
            inicio=fin - timedelta(hours=6),
            fin=fin,
        )
    )
    await sesion.flush()

    r = await progreso.recuperacion(sesion, usuario.id, DOMINGO, 3)

    assert [s.inicio for s in r.semanas] == [
        date(2026, 9, 21),
        date(2026, 9, 28),
        date(2026, 10, 5),
    ]
    # Las dos primeras semanas tienen menos de 28 dias de historia: sin ACWR.
    assert [s.acwr for s in r.semanas[:2]] == [None, None]
    assert [s.semaforo for s in r.semanas[:2]] == [None, None]
    ultima = r.semanas[2]
    assert ultima.carga_semanal == 2000
    assert ultima.acwr == 1.081
    assert ultima.semaforo == "verde"
    assert ultima.en_curso is False
    assert ultima.sueno_prom_h == 6.0
    assert ultima.sueno_dias_con_dato == 1
    assert r.semanas[0].sueno_prom_h is None  # sin registros: NULL, no 0
    assert (r.bandas.min_seguro, r.bandas.max_seguro, r.bandas.alerta) == (
        0.8,
        1.3,
        1.5,
    )
    assert "zona segura (ACWR 1,08)" in r.conclusion
    assert "6 h de promedio" in r.conclusion
    assert "por debajo de tu objetivo de 7 h" in r.conclusion


async def test_recuperacion_semana_en_curso_se_marca(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    r = await progreso.recuperacion(sesion, usuario.id, date(2026, 10, 8), 2)
    assert [s.en_curso for s in r.semanas] == [False, True]
    assert all(s.acwr is None for s in r.semanas)
    assert "Aún no se puede calcular el ACWR" in r.conclusion


# ------------------------------------------------------ 4. ¿Voy hacia 11 %? --


async def test_composicion_toma_el_ultimo_registro_de_cada_semana(
    sesion: AsyncSession, usuario: Usuario
) -> None:
    for fecha, peso, cintura in (
        (date(2026, 9, 21), "80.00", "90.0"),
        (date(2026, 9, 24), "79.60", None),  # ultimo de su semana, sin cintura
        (date(2026, 10, 5), "79.00", "88.5"),
    ):
        sesion.add(
            MedidaCorporal(
                usuario_id=usuario.id,
                fecha=fecha,
                peso_kg=Decimal(peso),
                cintura_cm=Decimal(cintura) if cintura else None,
            )
        )
    await sesion.flush()

    r = await progreso.composicion(sesion, usuario.id, DOMINGO, 4)
    assert [(s.fecha_medida, s.peso_kg) for s in r.semanas] == [
        (date(2026, 9, 24), 79.6),
        (date(2026, 10, 5), 79.0),
    ]
    assert r.cambio_peso_kg == -0.6
    # Cintura: solo la semana del 5/10 la tiene, no hay con que comparar.
    assert r.cambio_cintura_cm is None
    # El seed fija el peso objetivo en 75 kg: 79,0 - 75 = 4.
    assert r.peso_objetivo_kg == 75.0
    assert r.conclusion.startswith("En 2 semanas con medición bajaste 0,6 kg")
    assert "te faltan 4 kg para tu objetivo de 75 kg" in r.conclusion
    assert r.conclusion.endswith("El peso solo no mide la grasa.")


async def test_composicion_endpoint_sin_datos(cliente: AsyncClient) -> None:
    r = await cliente.get("/api/v1/progreso/composicion")
    assert r.status_code == 200
    assert r.json()["semanas"] == []
    assert r.json()["conclusion"] == "Todavía no hay mediciones de peso."


@pytest.mark.parametrize("ruta", ["rendimiento", "recuperacion"])
async def test_endpoints_sin_datos_responden_200(
    cliente: AsyncClient, ruta: str
) -> None:
    assert (await cliente.get(f"/api/v1/progreso/{ruta}")).status_code == 200


async def test_ventana_de_semanas_fuera_de_rango_es_422(cliente: AsyncClient) -> None:
    assert (
        await cliente.get("/api/v1/progreso/recuperacion?semanas=0")
    ).status_code == 422
    assert (
        await cliente.get("/api/v1/progreso/composicion?semanas=999")
    ).status_code == 422


# ------------------------------------------------------- frases (unitarias) --


def test_num_no_recorta_ceros_enteros() -> None:
    # Regresion: con 0 decimales "50" salia como "5".
    assert conclusiones.num(50.0, 0) == "50"
    assert conclusiones.num(100.0, 0) == "100"
    assert conclusiones.num(10.0) == "10"


def test_num_usa_coma_y_sin_ceros_de_relleno() -> None:
    assert conclusiones.num(7.0) == "7"
    assert conclusiones.num(7.3) == "7,3"
    assert conclusiones.num(1.081, 2) == "1,08"


def test_composicion_con_objetivo_dice_cuanto_falta() -> None:
    filas = [
        SemanaComposicion(
            inicio=date(2026, 9, 21),
            fecha_medida=date(2026, 9, 21),
            peso_kg=80.0,
            cintura_cm=None,
        ),
        SemanaComposicion(
            inicio=date(2026, 9, 28),
            fecha_medida=date(2026, 9, 28),
            peso_kg=79.0,
            cintura_cm=None,
        ),
    ]
    texto = conclusiones.composicion(filas, -1.0, None, 77.0)
    assert "te faltan 2 kg para tu objetivo de 77 kg" in texto
