"""Orquestacion de sesion + bloques en una sola operacion.

El cliente (Fase 5 offline-first) puede reintentar el mismo POST con el
mismo `idempotency_key`: el repo de sesion es idempotente, pero los
bloques que se crearon la primera vez YA EXISTEN. Insertar otra vez
provocaria violacion de UNIQUE(sesion_id, orden).

Estrategia: comparamos la cantidad de bloques que la sesion ya tiene
contra la cantidad que el cliente envia. Si la sesion no tiene bloques,
es la primera vez (los creamos). Si ya tiene, es un retry (no hacemos
nada, devolvemos lo que hay).
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Bloque, Sesion
from app.repositories import entrenamiento as repo
from app.schemas.entrenamiento.sesion import (
    BloqueSinSesionCreate,
    SesionCreate,
    SesionUpdate,
)
from app.services.entrenamiento.bloque import validar_campos


async def _validar_bloques(
    session: AsyncSession, bloques_payload: list[BloqueSinSesionCreate]
) -> None:
    ejercicios = {
        e.id: e
        for e in await repo.listar_ejercicios_por_ids(
            session, [b.ejercicio_id for b in bloques_payload]
        )
    }
    for b in bloques_payload:
        ejercicio = ejercicios.get(b.ejercicio_id)
        if ejercicio is None:
            raise RecursoNoEncontradoError(f"ejercicio {b.ejercicio_id} no encontrado")
        validar_campos(
            ejercicio.tipo_medicion,
            ejercicio_nombre=ejercicio.nombre,
            series=b.series,
            reps=b.reps,
            peso=b.peso_kg,
            distancia=b.distancia_m,
            duracion=b.duracion_s,
            calidad=b.calidad,
        )


async def crear_sesion_con_bloques(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    sesion: SesionCreate,
    bloques_payload: list[BloqueSinSesionCreate],
) -> tuple[Sesion, int]:
    """Devuelve (sesion, bloques_creados). Si bloques_creados es 0, el
    `idempotency_key` ya existia: los bloques que devuelve son los que
    estaban."""
    await _validar_bloques(session, bloques_payload)

    sesion_creada = await repo.crear_sesion(
        session,
        sesion_id=sesion.id,
        idempotency_key=sesion.idempotency_key,
        usuario_id=usuario_id,
        sesion_plan_id=sesion.sesion_plan_id,
        fecha=sesion.fecha,
        tipo_sesion_id=sesion.tipo_sesion_id,
        duracion_min=sesion.duracion_min,
        rpe=sesion.rpe,
        nota=sesion.nota,
    )
    await session.flush()

    existentes = (
        await session.scalar(
            select(func.count())
            .select_from(Bloque)
            .where(Bloque.sesion_id == sesion_creada.id)
        )
        or 0
    )

    creadas = 0
    if existentes == 0 and bloques_payload:
        for b in bloques_payload:
            await repo.crear_bloque(
                session,
                sesion_id=sesion_creada.id,
                ejercicio_id=b.ejercicio_id,
                orden=b.orden,
                series=b.series,
                reps=b.reps,
                distancia_m=b.distancia_m,
                duracion_s=b.duracion_s,
                calidad=b.calidad,
                peso_kg=b.peso_kg,
                rpe=b.rpe,
                dolor_lumbar=b.dolor_lumbar,
            )
            creadas += 1

    await session.commit()
    # attribute_names=["bloques"]: SesionRead siempre incluye los bloques,
    # asi que el service es quien los deja cargados antes de devolver.
    await session.refresh(sesion_creada, attribute_names=["bloques"])
    return sesion_creada, creadas


async def listar_sesiones_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Sesion]:
    return await repo.listar_sesiones_por_fecha(session, usuario_id, fecha)


async def obtener_sesion(
    session: AsyncSession, usuario_id: uuid.UUID, sesion_id: uuid.UUID
) -> Sesion:
    sesion = await repo.obtener_sesion_por_id(session, sesion_id)
    if sesion is None or sesion.usuario_id != usuario_id:
        # Mismo tratamiento que un 404 real: no filtrar si la sesion existe
        # pero es de otro usuario.
        raise RecursoNoEncontradoError(f"sesion {sesion_id} no encontrada")
    return sesion


async def actualizar_sesion(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    sesion_id: uuid.UUID,
    payload: SesionUpdate,
) -> Sesion:
    """PUT reemplaza cabecera y bloques completos, igual que
    reemplazar_composicion: declarar todo de una vez evita bloques viejos
    de un `orden` que ya no existe."""
    sesion = await obtener_sesion(session, usuario_id, sesion_id)
    bloques_payload = payload.bloques or []
    await _validar_bloques(session, bloques_payload)

    await repo.actualizar_sesion(
        session,
        sesion,
        fecha=payload.fecha,
        tipo_sesion_id=payload.tipo_sesion_id,
        duracion_min=payload.duracion_min,
        rpe=payload.rpe,
        nota=payload.nota,
    )

    await repo.eliminar_bloques_de_sesion(session, sesion.id)
    # El DELETE de arriba es a nivel Core: el ORM todavia tiene los bloques
    # viejos cargados en sesion.bloques (via selectinload de obtener_sesion).
    # Sin expirar, el flush los ve "todavia asociados" e intenta poner
    # sesion_id=NULL en filas que ya no existen.
    session.expire(sesion, ["bloques"])
    for b in bloques_payload:
        await repo.crear_bloque(
            session,
            sesion_id=sesion.id,
            ejercicio_id=b.ejercicio_id,
            orden=b.orden,
            series=b.series,
            reps=b.reps,
            distancia_m=b.distancia_m,
            duracion_s=b.duracion_s,
            calidad=b.calidad,
            peso_kg=b.peso_kg,
            rpe=b.rpe,
            dolor_lumbar=b.dolor_lumbar,
        )

    await session.commit()
    # carga_srpe es Computed: el UPDATE la deja expirada (no vino con
    # RETURNING como el INSERT de crear_sesion). Sin refrescarla acá, el
    # primer acceso pasa a ser un lazy-load fuera del greenlet async, y
    # FastAPI lo pisa al serializar la respuesta.
    await session.refresh(sesion, attribute_names=["bloques", "carga_srpe"])
    return sesion


async def eliminar_sesion(
    session: AsyncSession, usuario_id: uuid.UUID, sesion_id: uuid.UUID
) -> None:
    sesion = await obtener_sesion(session, usuario_id, sesion_id)
    await repo.eliminar_sesion(session, sesion)
    await session.commit()
