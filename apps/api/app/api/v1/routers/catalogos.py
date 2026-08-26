"""Endpoints de catalogos sembrados (Fase 1). El usuario no crea valores:
solo lee.

Estos endpoints existen para que el frontend pueda poblar los formularios
de seleccion (tipo de sesion en Entreno, ejercicio en un bloque, zona
corporal en una molestia). Sin esto el front tendria que hardcodear los
valores, lo que rompe cuando el seed agrega uno nuevo.

`ejercicio` es la excepcion (REGLAS_NEGOCIO §15): el usuario lo amplia
inline, el universo de ejercicios de una rutina real es abierto.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.db.session import get_session
from app.models import TipoSesion, TipoTest, Usuario, ZonaCorporal
from app.models.enums import TipoMedicion
from app.schemas.catalogo.catalogo import (
    EjercicioCreate,
    EjercicioDetalleRead,
    EjercicioFusionarCreate,
    EjercicioListRead,
    EjercicioRead,
    EjercicioUpdate,
    FusionResultadoRead,
    TipoSesionRead,
    TipoTestRead,
    ZonaCorporalRead,
)
from app.services.catalogo import entrenamiento as service

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get(
    "/tipos-sesion",
    response_model=list[TipoSesionRead],
    summary="Lista los tipos de sesion sembrados.",
)
async def listar_tipos_sesion(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[TipoSesion]:
    return await service.listar_tipos_sesion(sesion)


@router.get(
    "/ejercicios",
    response_model=EjercicioListRead,
    summary="Lista los ejercicios con busqueda, filtros y orden.",
)
async def listar_ejercicios(
    q: str | None = Query(default=None, description="busca en nombre y descripcion"),
    tipo_medicion: TipoMedicion | None = Query(default=None),
    tipo_sesion_id: int | None = Query(default=None),
    activo: bool = Query(default=True, description="false lista los archivados"),
    orden: Literal["nombre", "uso", "reciente"] = Query(default="nombre"),
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> EjercicioListRead:
    return await service.listar_ejercicios_filtrado(
        sesion,
        q=q,
        tipo_medicion=tipo_medicion,
        tipo_sesion_id=tipo_sesion_id,
        activo=activo,
        orden=orden,
    )


@router.get(
    "/ejercicios/{ejercicio_id}",
    response_model=EjercicioDetalleRead,
    summary="Detalle del ejercicio: datos + historial + duplicados.",
)
async def obtener_detalle_ejercicio(
    ejercicio_id: int = Path(..., description="id del ejercicio"),
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> EjercicioDetalleRead:
    return await service.obtener_detalle_ejercicio(sesion, ejercicio_id)


@router.post(
    "/ejercicios",
    response_model=EjercicioRead,
    status_code=status.HTTP_200_OK,
    summary="Crea un ejercicio. Unico catalogo que el usuario puede ampliar.",
)
async def crear_ejercicio(
    payload: EjercicioCreate,
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> EjercicioRead:
    """`model_dump(exclude_unset=True)` para que el service sepa qué campos
    vinieron en el body y cuáles no: el service aplica solo los cambios."""
    ejercicio = await service.crear_ejercicio(
        sesion, payload.model_dump(exclude_unset=True)
    )
    return EjercicioRead.model_validate(ejercicio)


@router.patch(
    "/ejercicios/{ejercicio_id}",
    response_model=EjercicioRead,
    summary="Edita ejercicio. tipo_medicion NO es editable (REGLAS_NEGOCIO §15).",
)
async def actualizar_ejercicio(
    payload: EjercicioUpdate,
    ejercicio_id: int = Path(..., description="id del ejercicio"),
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> EjercicioRead:
    """`tipo_medicion` queda afuera del payload (extra=forbid en el schema):
    cambiarlo invalidaria los bloques historicos (REGLAS_NEGOCIO §15).
    `descripcion=""` se traduce a None en el service."""
    ejercicio = await service.actualizar_ejercicio(
        sesion, ejercicio_id, payload.model_dump(exclude_unset=True)
    )
    return EjercicioRead.model_validate(ejercicio)


@router.post(
    "/ejercicios/{ejercicio_id}/fusionar",
    response_model=FusionResultadoRead,
    status_code=status.HTTP_200_OK,
    summary="Fusiona origen en destino. Reasigna bloques y archiva origen.",
)
async def fusionar_ejercicio(
    payload: EjercicioFusionarCreate,
    ejercicio_id: int = Path(..., description="id del ejercicio origen"),
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> FusionResultadoRead:
    """`ejercicio_id` (path) es el origen; `payload.destino_id` es el que se
    queda. Reasigna los bloques reales y planeados del origen al destino en
    una sola transaccion, y archiva el origen (no lo borra). Devuelve los
    conteos de filas reasignadas por tabla (design #326)."""
    return await service.fusionar_ejercicios(
        sesion, origen_id=ejercicio_id, destino_id=payload.destino_id
    )


@router.delete(
    "/ejercicios/{ejercicio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina un ejercicio. Solo si uso == 0 y no aparece en bloque_plan.",
)
async def eliminar_ejercicio(
    ejercicio_id: int = Path(..., description="id del ejercicio"),
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> None:
    """DELETE fisico: solo procede si el ejercicio no tiene bloques reales ni
    planeados. Si los tiene, devuelve 409 con un mensaje que sugiere
    archivarlo o fusionarlo: asi la UI puede mostrar la salida concreta."""
    await service.eliminar_ejercicio(sesion, ejercicio_id)


@router.get(
    "/zonas-corporales",
    response_model=list[ZonaCorporalRead],
    summary="Lista las zonas corporales sembradas.",
)
async def listar_zonas_corporales(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[ZonaCorporal]:
    return await service.listar_zonas_corporales(sesion)


@router.get(
    "/tipos-test",
    response_model=list[TipoTestRead],
    summary="Lista los tipos de test fisico sembrados.",
)
async def listar_tipos_test(
    _: Usuario = Depends(get_usuario_actual),
    sesion: AsyncSession = Depends(get_session),
) -> list[TipoTest]:
    return await service.listar_tipos_test(sesion)
