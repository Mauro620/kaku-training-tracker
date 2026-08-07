"""Endpoints de test_fisico, medida_corporal y partido (Fase 7,
ROADMAP §7, REGLAS_NEGOCIO §7-8)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import MedidaCorporal, Partido, TestFisico, Usuario
from app.schemas.evaluacion.medida import MedidaCorporalCreate, MedidaCorporalRead
from app.schemas.evaluacion.partido import PartidoCreate, PartidoRead
from app.schemas.evaluacion.test_fisico import (
    ResultadoTestRead,
    TestFisicoCreate,
    TestFisicoRead,
)
from app.services.evaluacion import medida as medida_service
from app.services.evaluacion import partido as partido_service
from app.services.evaluacion import test_fisico as test_service

router = APIRouter(tags=["evaluacion"])


@router.post(
    "/tests",
    response_model=TestFisicoRead,
    status_code=status.HTTP_200_OK,
    summary="Registra un test fisico con sus intentos.",
)
async def registrar_test(
    payload: TestFisicoCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> TestFisico:
    return await test_service.registrar_test(
        sesion,
        usuario.id,
        idempotency_key=payload.idempotency_key,
        fecha=payload.fecha,
        tipo_test_id=payload.tipo_test_id,
        superficie=payload.superficie,
        condiciones=payload.condiciones,
        valores=payload.valores,
    )


@router.get(
    "/tests",
    response_model=list[TestFisicoRead],
    summary="Tests fisicos de una fecha.",
)
async def listar_tests(
    fecha: date = Query(..., description="Fecha local del registro"),
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[TestFisico]:
    return await test_service.listar_tests_de_fecha(sesion, usuario.id, fecha)


@router.get(
    "/tests/{test_id}",
    response_model=TestFisicoRead,
    summary="Detalle de un test fisico, con sus intentos.",
)
async def obtener_test(
    test_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> TestFisico:
    return await test_service.obtener_test(sesion, usuario.id, test_id)


@router.get(
    "/tests/{test_id}/resultado",
    response_model=ResultadoTestRead,
    summary="Mejor, media, pct_decremento (solo rsa_30m) y pct_cambio.",
)
async def obtener_resultado_test(
    test_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> ResultadoTestRead:
    test = await test_service.obtener_test(sesion, usuario.id, test_id)
    resultado = await test_service.calcular_resultado(sesion, usuario.id, test)
    return ResultadoTestRead(
        mejor=resultado.mejor,
        media=resultado.media,
        pct_decremento=resultado.pct_decremento,
        pct_cambio=resultado.pct_cambio,
    )


@router.delete(
    "/tests/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina un test fisico y sus intentos.",
)
async def eliminar_test(
    test_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    await test_service.eliminar_test(sesion, usuario.id, test_id)


@router.post(
    "/medidas",
    response_model=MedidaCorporalRead,
    status_code=status.HTTP_200_OK,
    summary="Registra (upsert) la medida corporal de una fecha.",
)
async def registrar_medida(
    payload: MedidaCorporalCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> MedidaCorporal:
    return await medida_service.registrar_medida(
        sesion,
        usuario.id,
        fecha=payload.fecha,
        peso_kg=payload.peso_kg,
        fc_reposo=payload.fc_reposo,
    )


@router.get(
    "/medidas",
    response_model=list[MedidaCorporalRead],
    summary="Lista las medidas corporales del usuario, mas reciente primero.",
)
async def listar_medidas(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[MedidaCorporal]:
    return await medida_service.listar_medidas(sesion, usuario.id)


@router.post(
    "/partidos",
    response_model=PartidoRead,
    status_code=status.HTTP_200_OK,
    summary="Registra la ficha de un partido sobre una sesion existente.",
)
async def registrar_partido(
    payload: PartidoCreate,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Partido:
    return await partido_service.registrar_partido(
        sesion,
        usuario.id,
        sesion_id=payload.sesion_id,
        rival=payload.rival,
        formato=payload.formato,
        minutos_jugados=payload.minutos_jugados,
        goles=payload.goles,
        asistencias=payload.asistencias,
        recuperaciones=payload.recuperaciones,
        salio_bien=payload.salio_bien,
        a_ajustar=payload.a_ajustar,
    )


@router.get(
    "/partidos",
    response_model=list[PartidoRead],
    summary="Lista los partidos del usuario, mas reciente primero.",
)
async def listar_partidos(
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[Partido]:
    return await partido_service.listar_partidos(sesion, usuario.id)


@router.get(
    "/partidos/{partido_id}",
    response_model=PartidoRead,
    summary="Detalle de un partido.",
)
async def obtener_partido(
    partido_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> Partido:
    return await partido_service.obtener_partido(sesion, usuario.id, partido_id)
