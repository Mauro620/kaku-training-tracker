"""Criterio de aceptación de la fase 1.

Crea el esquema desde cero en una base aparte, lo siembra y verifica que las
columnas generadas calculan bien y que los CHECK rechazan lo que tienen que
rechazar. Corre contra Postgres real: `Computed`, los enums nativos y
`EXTRACT(EPOCH ...)` no existen en SQLite.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.models import (
    Alimento,
    Ejercicio,
    Habito,
    Molestia,
    Parametro,
    RegistroBienestar,
    RegistroSueno,
    Serie,
    Sesion,
    TipoSesion,
    Usuario,
    ZonaCorporal,
)
from app.seeds.__main__ import sembrar
from app.seeds.catalogos import TIPOS_SESION, ZONAS_CORPORALES
from app.seeds.parametros import PARAMETROS

NOMBRE_USUARIO = "Test"


async def _recrear_base(url_admin: str, nombre: str) -> None:
    motor = create_async_engine(url_admin, isolation_level="AUTOCOMMIT")
    async with motor.connect() as conexion:
        await conexion.execute(text(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)'))
        await conexion.execute(text(f'CREATE DATABASE "{nombre}"'))
    await motor.dispose()


async def _preparar(url: str) -> None:
    motor = create_async_engine(url)
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(motor)() as s:
        await sembrar(s, NOMBRE_USUARIO)
        await s.commit()
    await motor.dispose()


@pytest.fixture(scope="session")
def url_base_de_prueba() -> str:
    """Base limpia por corrida: se crea, se migra y se siembra UNA vez.

    Fixture síncrona a propósito: una async con scope de sesión necesitaría un
    event loop compartido entre fixtures y tests, y no vale la complejidad.
    """
    settings = get_settings()
    nombre = f"{settings.postgres_db}_test"
    asyncio.run(_recrear_base(settings.dsn("postgres"), nombre))
    asyncio.run(_preparar(settings.test_database_url))
    return settings.test_database_url


@pytest.fixture
async def sesion(url_base_de_prueba: str) -> AsyncGenerator[AsyncSession, None]:
    """Cada test corre dentro de una transacción que se revierte al terminar.

    `join_transaction_mode="create_savepoint"` hace que los `commit()` del test
    caigan en un SAVEPOINT: se ven dentro del test y desaparecen con el
    rollback de afuera. Sin esto habría que recrear el esquema en cada test, que
    era lo que hacía la suite tres veces más lenta.
    """
    motor = create_async_engine(url_base_de_prueba)
    async with motor.connect() as conexion:
        transaccion = await conexion.begin()
        s = AsyncSession(
            bind=conexion,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield s
        finally:
            await s.close()
            await transaccion.rollback()
    await motor.dispose()


async def _ids_base(s: AsyncSession) -> tuple[uuid.UUID, int]:
    usuario_id = await s.scalar(select(Usuario.id))
    tipo_sesion_id = await s.scalar(
        select(TipoSesion.id).where(TipoSesion.codigo == "fuerza")
    )
    assert usuario_id is not None and tipo_sesion_id is not None
    return usuario_id, tipo_sesion_id


# ---------------------------------------------------------------- seeds ----


async def test_el_seed_deja_los_catalogos_completos(sesion: AsyncSession) -> None:
    esperado = {
        Parametro: len(PARAMETROS),
        TipoSesion: len(TIPOS_SESION),
        ZonaCorporal: len(ZONAS_CORPORALES),
        Ejercicio: 29,
        Alimento: 24,
        Habito: 4,
        Usuario: 1,
    }
    for modelo, cantidad in esperado.items():
        assert await sesion.scalar(select(func.count()).select_from(modelo)) == cantidad


async def test_el_seed_es_idempotente(sesion: AsyncSession) -> None:
    antes = await sesion.scalar(select(func.count()).select_from(Parametro))
    for _ in range(2):
        await sembrar(sesion, NOMBRE_USUARIO)
        await sesion.commit()

    assert await sesion.scalar(select(func.count()).select_from(Parametro)) == antes
    assert await sesion.scalar(select(func.count()).select_from(Usuario)) == 1


async def test_estan_los_parametros_que_las_reglas_referencian(
    sesion: AsyncSession,
) -> None:
    """Cada umbral que REGLAS_NEGOCIO nombra tiene que existir, o el servicio
    que lo lea va a terminar hardcodeando el número."""
    claves = set((await sesion.scalars(select(Parametro.clave))).all())
    referenciadas = {
        "sueno_objetivo_horas",
        "acwr_max_seguro",
        "acwr_umbral_alerta",
        "cmj_caida_alerta_pct",
        "estado_banda_verde",
        "estado_banda_amarilla",
        "estado_penal_sueno_por_hora",
        "estado_penal_sueno_tope",
        "estado_penal_hooper_por_punto",
        "estado_penal_hooper_tope",
        "estado_penal_acwr_moderado",
        "estado_penal_acwr_alto",
        "estado_penal_molestia_por_punto",
        "estado_penal_molestia_tope",
        "estado_penal_cmj",
        "hooper_base_ventana_dias",
        "hooper_base_min_registros",
        "molestia_recurrencia_dias",
        "molestia_recurrencia_conteo",
        "cerveza_horas_sin_alta_demanda",
        "cerveza_acwr_max",
        "cerveza_deuda_sueno_max",
        "rsa_decremento_bueno_pct",
        "rsa_decremento_alerta_pct",
    }
    assert referenciadas <= claves


# ------------------------------------------------- columnas generadas ----


@pytest.mark.parametrize(
    ("rpe", "duracion_min", "carga_srpe"),
    [(8, 60, 480), (5, 45, 225)],  # REGLAS_NEGOCIO §1, casos del documento
)
async def test_carga_srpe_se_calcula_sola(
    sesion: AsyncSession, rpe: int, duracion_min: int, carga_srpe: int
) -> None:
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    entrenamiento = Sesion(
        usuario_id=usuario_id,
        fecha=date(2026, 8, 4),
        tipo_sesion_id=tipo_sesion_id,
        duracion_min=duracion_min,
        rpe=rpe,
        idempotency_key=uuid.uuid4(),
    )
    sesion.add(entrenamiento)
    await sesion.commit()
    await sesion.refresh(entrenamiento)

    assert entrenamiento.carga_srpe == carga_srpe


async def test_horas_sueno_se_calcula_sola(sesion: AsyncSession) -> None:
    usuario_id, _ = await _ids_base(sesion)
    registro = RegistroSueno(
        usuario_id=usuario_id,
        fecha=date(2026, 8, 4),
        inicio=datetime(2026, 8, 3, 23, 30, tzinfo=UTC),
        fin=datetime(2026, 8, 4, 7, 0, tzinfo=UTC),
    )
    sesion.add(registro)
    await sesion.commit()
    await sesion.refresh(registro)

    assert registro.horas_sueno == Decimal("7.50")


async def test_hooper_es_la_suma_de_los_cuatro_items(sesion: AsyncSession) -> None:
    usuario_id, _ = await _ids_base(sesion)
    registro = RegistroBienestar(
        usuario_id=usuario_id,
        fecha=date(2026, 8, 4),
        sueno_pobre=2,
        fatiga=3,
        dolor_muscular=1,
        estres=4,
    )
    sesion.add(registro)
    await sesion.commit()
    await sesion.refresh(registro)

    assert registro.hooper == 10


# ------------------------------------------------------------- CHECKs ----


async def test_rechaza_rpe_fuera_de_rango(sesion: AsyncSession) -> None:
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    sesion.add(
        Sesion(
            usuario_id=usuario_id,
            fecha=date(2026, 8, 4),
            tipo_sesion_id=tipo_sesion_id,
            duracion_min=60,
            rpe=11,
            idempotency_key=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.commit()


async def test_rechaza_duracion_no_positiva(sesion: AsyncSession) -> None:
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    sesion.add(
        Sesion(
            usuario_id=usuario_id,
            fecha=date(2026, 8, 4),
            tipo_sesion_id=tipo_sesion_id,
            duracion_min=0,
            rpe=5,
            idempotency_key=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.commit()


@pytest.mark.parametrize("item", ["sueno_pobre", "fatiga", "dolor_muscular", "estres"])
@pytest.mark.parametrize("valor", [0, 6])
async def test_rechaza_bienestar_fuera_de_1_a_5(
    sesion: AsyncSession, item: str, valor: int
) -> None:
    usuario_id, _ = await _ids_base(sesion)
    campos = dict.fromkeys(("sueno_pobre", "fatiga", "dolor_muscular", "estres"), 3)
    campos[item] = valor
    sesion.add(
        RegistroBienestar(usuario_id=usuario_id, fecha=date(2026, 8, 4), **campos)
    )
    with pytest.raises(IntegrityError):
        await sesion.commit()


async def test_rechaza_fin_anterior_a_inicio(sesion: AsyncSession) -> None:
    usuario_id, _ = await _ids_base(sesion)
    sesion.add(
        RegistroSueno(
            usuario_id=usuario_id,
            fecha=date(2026, 8, 4),
            inicio=datetime(2026, 8, 4, 7, 0, tzinfo=UTC),
            fin=datetime(2026, 8, 3, 23, 30, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.commit()


@pytest.mark.parametrize("intensidad", [0, 11])
async def test_rechaza_intensidad_de_molestia_fuera_de_1_a_10(
    sesion: AsyncSession, intensidad: int
) -> None:
    """El 0 es imposible por definición: sin molestia no hay fila."""
    usuario_id, _ = await _ids_base(sesion)
    zona_id = await sesion.scalar(
        select(ZonaCorporal.id).where(ZonaCorporal.nombre == "lumbar")
    )
    sesion.add(
        Molestia(
            usuario_id=usuario_id,
            fecha=date(2026, 8, 4),
            zona_id=zona_id,
            intensidad=intensidad,
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.commit()


async def test_rechaza_rpe_de_serie_fuera_de_rango(sesion: AsyncSession) -> None:
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    entrenamiento = Sesion(
        usuario_id=usuario_id,
        fecha=date(2026, 8, 4),
        tipo_sesion_id=tipo_sesion_id,
        duracion_min=60,
        rpe=8,
        idempotency_key=uuid.uuid4(),
    )
    sesion.add(entrenamiento)
    await sesion.commit()

    ejercicio_id = await sesion.scalar(select(Ejercicio.id))
    sesion.add(
        Serie(
            sesion_id=entrenamiento.id,
            ejercicio_id=ejercicio_id,
            orden=1,
            series=4,
            reps=6,
            rpe=0,
        )
    )
    with pytest.raises(IntegrityError):
        await sesion.commit()


# ------------------------------------------------------------ unicidad ----


async def test_un_solo_registro_de_sueno_por_fecha(sesion: AsyncSession) -> None:
    """La unicidad (usuario_id, fecha) es la deduplicación de la cola de sync."""
    usuario_id, _ = await _ids_base(sesion)
    for _ in range(2):
        sesion.add(
            RegistroSueno(
                usuario_id=usuario_id,
                fecha=date(2026, 8, 4),
                inicio=datetime(2026, 8, 3, 23, 0, tzinfo=UTC),
                fin=datetime(2026, 8, 4, 7, 0, tzinfo=UTC),
            )
        )
    with pytest.raises(IntegrityError):
        await sesion.commit()


async def test_idempotency_key_de_sesion_es_unica(sesion: AsyncSession) -> None:
    usuario_id, tipo_sesion_id = await _ids_base(sesion)
    clave = uuid.uuid4()
    for _ in range(2):
        sesion.add(
            Sesion(
                usuario_id=usuario_id,
                fecha=date(2026, 8, 4),
                tipo_sesion_id=tipo_sesion_id,
                duracion_min=60,
                rpe=8,
                idempotency_key=clave,
            )
        )
    with pytest.raises(IntegrityError):
        await sesion.commit()
