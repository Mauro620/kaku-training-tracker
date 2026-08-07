"""Reglas de negocio de test_fisico (REGLAS_NEGOCIO §7 y §8)."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import TestFisico
from app.repositories import evaluacion as repo
from app.services.evaluacion.calculo import (
    calcular_pct_cambio,
    calcular_pct_decremento,
    mejor_intento,
)

_CODIGO_RSA = "rsa_30m"


@dataclass(frozen=True)
class ResultadoTest:
    mejor: Decimal
    media: Decimal
    pct_decremento: Decimal | None
    pct_cambio: Decimal | None


async def registrar_test(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    idempotency_key: uuid.UUID,
    fecha: date,
    tipo_test_id: int,
    superficie: str | None,
    condiciones: str | None,
    valores: list[Decimal],
) -> TestFisico:
    tipo = await repo.obtener_tipo_test_por_id(session, tipo_test_id)
    if tipo is None:
        raise RecursoNoEncontradoError(f"tipo_test {tipo_test_id} no encontrado")

    test = await repo.crear_test_fisico(
        session,
        usuario_id=usuario_id,
        idempotency_key=idempotency_key,
        fecha=fecha,
        tipo_test_id=tipo_test_id,
        superficie=superficie,
        condiciones=condiciones,
    )
    existentes = await repo.contar_intentos(session, test.id)
    if existentes == 0:
        await repo.agregar_intentos(session, test.id, valores)
    await session.commit()

    test_completo = await repo.obtener_test_fisico_por_id(session, test.id)
    assert test_completo is not None
    return test_completo


async def obtener_test(
    session: AsyncSession, usuario_id: uuid.UUID, test_fisico_id: uuid.UUID
) -> TestFisico:
    test = await repo.obtener_test_fisico_por_id(session, test_fisico_id)
    if test is None or test.usuario_id != usuario_id:
        raise RecursoNoEncontradoError(f"test_fisico {test_fisico_id} no encontrado")
    return test


async def eliminar_test(
    session: AsyncSession, usuario_id: uuid.UUID, test_fisico_id: uuid.UUID
) -> None:
    test = await obtener_test(session, usuario_id, test_fisico_id)
    await repo.eliminar_intentos(session, test.id)
    await repo.eliminar_test_fisico(session, test)
    await session.commit()


async def listar_tests_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[TestFisico]:
    return await repo.listar_tests_por_fecha(session, usuario_id, fecha)


async def calcular_resultado(
    session: AsyncSession, usuario_id: uuid.UUID, test: TestFisico
) -> ResultadoTest:
    tipo = await repo.obtener_tipo_test_por_id(session, test.tipo_test_id)
    assert tipo is not None  # FK garantiza que existe

    valores = [i.valor for i in test.intentos]
    mejor = mejor_intento(valores, tipo.mejor_es_mayor)
    # quantize a 3 decimales: valor.numero(7,3) en el catalogo, y una
    # division exacta desborda esos digitos (ej. 12.83/3 repite infinito).
    media = (sum(valores, Decimal("0")) / len(valores)).quantize(Decimal("0.001"))

    pct_decremento = (
        calcular_pct_decremento(valores) if tipo.codigo == _CODIGO_RSA else None
    )

    # valor_base = mejor resultado del PRIMER test registrado de este tipo
    # (REGLAS_NEGOCIO §8). Si el test actual es el primero, no hay con que
    # comparar.
    historial = await repo.listar_tests_por_tipo(session, usuario_id, tipo.id)
    pct_cambio: Decimal | None = None
    if historial and historial[0].id != test.id:
        primero = historial[0]
        valor_base = mejor_intento(
            [i.valor for i in primero.intentos], tipo.mejor_es_mayor
        )
        pct_cambio = calcular_pct_cambio(valor_base, mejor, tipo.mejor_es_mayor)

    return ResultadoTest(
        mejor=mejor, media=media, pct_decremento=pct_decremento, pct_cambio=pct_cambio
    )
