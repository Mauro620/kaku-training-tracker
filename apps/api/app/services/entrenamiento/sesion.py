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
from app.models import Bloque, BloquePlan, Sesion
from app.repositories import entrenamiento as repo
from app.repositories.bienestar import molestia as repo_molestia
from app.schemas.entrenamiento.sesion import (
    BloqueDeltaRead,
    BloqueDetalleRead,
    BloqueEjercicioEnDetalleRead,
    BloqueNoEjecutadoRead,
    BloqueObjetivoRead,
    BloqueSinSesionCreate,
    MolestiaDetalleRead,
    PlanCicloRead,
    PlanDetalleEnSesionRead,
    SesionCreate,
    SesionDeltaRead,
    SesionDetalleRead,
    SesionTipoRead,
    SesionUpdate,
)
from app.services.catalogo.delta import (
    BloqueDeltaInput,
    BloquePlanDeltaInput,
    SesionDeltaInput,
    SesionPlanDeltaInput,
    delta_bloque,
    delta_sesion,
)
from app.services.entrenamiento.bloque import validar_campos
from app.services.entrenamiento.plan import resolver_estado_de_plan


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
                nota=b.nota,
            )
            creadas += 1

    # El plan asociado pasa a cumplido o movido segun caiga la fecha
    # (PLAN_IMPORT.md 2.1). `estado` es columna persistida, no derivada: si
    # esta llamada falta, el importador cree que el plan sigue pendiente y lo
    # reemplaza, borrando planificacion que ya se ejecuto.
    if sesion_creada.sesion_plan_id is not None:
        await resolver_estado_de_plan(session, sesion_creada.sesion_plan_id)

    await session.commit()
    # attribute_names=["bloques"]: SesionRead siempre incluye los bloques,
    # asi que el service es quien los deja cargados antes de devolver.
    await session.refresh(sesion_creada, attribute_names=["bloques"])
    return sesion_creada, creadas


async def listar_sesiones_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Sesion]:
    return await repo.listar_sesiones_por_fecha(session, usuario_id, fecha)


async def listar_ultimas_sesiones(
    session: AsyncSession, usuario_id: uuid.UUID, limite: int
) -> list[Sesion]:
    return await repo.listar_ultimas_sesiones(session, usuario_id, limite)


async def obtener_sesion(
    session: AsyncSession, usuario_id: uuid.UUID, sesion_id: uuid.UUID
) -> Sesion:
    sesion = await repo.obtener_sesion_por_id(session, sesion_id)
    if sesion is None or sesion.usuario_id != usuario_id:
        # Mismo tratamiento que un 404 real: no filtrar si la sesion existe
        # pero es de otro usuario.
        raise RecursoNoEncontradoError(f"sesion {sesion_id} no encontrada")
    return sesion


def _armar_objetivo(bp: BloquePlan | None) -> BloqueObjetivoRead | None:
    if bp is None:
        return None
    return BloqueObjetivoRead(
        id=bp.id,
        orden=bp.orden,
        series=bp.series,
        reps_min=bp.reps_min,
        reps_max=bp.reps_max,
        peso_objetivo_kg=bp.peso_objetivo_kg,
        distancia_objetivo_m=bp.distancia_objetivo_m,
        duracion_objetivo_s=bp.duracion_objetivo_s,
        nota=bp.nota,
    )


def _armar_bloque_detalle(
    bloque: Bloque, bloque_plan: BloquePlan | None
) -> BloqueDetalleRead:
    """Convierte un bloque real (+ opcionalmente su plan) en el shape del
    detalle: campos del bloque + ejercicio anidado + objetivo (si lo
    tiene) + delta contra el objetivo (todas las keys NULL si no)."""
    ejercicio = bloque.ejercicio
    objetivo = _armar_objetivo(bloque_plan)
    delta_real = BloqueDeltaInput(
        series=bloque.series,
        reps=bloque.reps,
        peso_kg=bloque.peso_kg,
        distancia_m=bloque.distancia_m,
        duracion_s=bloque.duracion_s,
    )
    if bloque_plan is not None:
        delta_plan_input: BloquePlanDeltaInput | None = BloquePlanDeltaInput(
            series=bloque_plan.series,
            reps_min=bloque_plan.reps_min,
            reps_max=bloque_plan.reps_max,
            peso_objetivo_kg=bloque_plan.peso_objetivo_kg,
            distancia_objetivo_m=bloque_plan.distancia_objetivo_m,
            duracion_objetivo_s=bloque_plan.duracion_objetivo_s,
        )
    else:
        delta_plan_input = None
    resultado = delta_bloque(delta_real, delta_plan_input)
    return BloqueDetalleRead(
        id=bloque.id,
        sesion_id=bloque.sesion_id,
        orden=bloque.orden,
        series=bloque.series,
        reps=bloque.reps,
        distancia_m=bloque.distancia_m,
        duracion_s=bloque.duracion_s,
        calidad=bloque.calidad,
        peso_kg=bloque.peso_kg,
        rpe=bloque.rpe,
        dolor_lumbar=bloque.dolor_lumbar,
        nota=bloque.nota,
        ejercicio=BloqueEjercicioEnDetalleRead(
            id=ejercicio.id,
            nombre=ejercicio.nombre,
            tipo_medicion=ejercicio.tipo_medicion,
            descripcion=ejercicio.descripcion,
            carga_lumbar=ejercicio.carga_lumbar,
        ),
        objetivo=objetivo,
        delta=BloqueDeltaRead(
            series=resultado.series,
            reps=resultado.reps,
            peso_kg=resultado.peso_kg,
            distancia_m=resultado.distancia_m,
            duracion_s=resultado.duracion_s,
        ),
    )


def _armar_plan_detalle(
    sesion_actual: Sesion,
) -> PlanDetalleEnSesionRead | None:
    plan = sesion_actual.sesion_plan
    if plan is None:
        return None
    ciclo_detalle: PlanCicloRead | None = None
    if plan.ciclo_semana is not None and plan.ciclo_semana.ciclo is not None:
        ciclo = plan.ciclo_semana.ciclo
        ciclo_detalle = PlanCicloRead(
            numero=ciclo.numero,
            objetivo=ciclo.objetivo,
            semana=plan.ciclo_semana.numero,
            fase=plan.ciclo_semana.fase.value,
        )
    return PlanDetalleEnSesionRead(
        id=plan.id,
        nombre=plan.nombre,
        objetivo=plan.objetivo,
        nota=plan.nota,
        duracion_min_est=plan.duracion_min_est,
        rpe_objetivo=plan.rpe_objetivo,
        estado=plan.estado.value,
        dia_sugerido=plan.dia_sugerido,
        ciclo=ciclo_detalle,
    )


async def obtener_sesion_detalle(
    session: AsyncSession,
    sesion_id: uuid.UUID,
    *,
    usuario_id: uuid.UUID | None = None,
) -> SesionDetalleRead:
    """Construye el detalle completo de una sesion (R8, SPEC §3.7).

    `usuario_id` es opcional y filtra por dueño: si se omite, devuelve la
    sesion sin chequeo de pertenencia (uso interno entre servicios). El
    router siempre lo pasa."""
    sesion = await repo.obtener_sesion_con_detalle(session, sesion_id)
    if sesion is None or (
        usuario_id is not None and sesion.usuario_id != usuario_id
    ):
        raise RecursoNoEncontradoError(f"sesion {sesion_id} no encontrada")
    # `carga_srpe` es columna generada (REGLAS_NEGOCIO §1). El SELECT del
    # repo la trae, pero un flush posterior puede expirarla; el refresh
    # explicito evita un lazy-load fuera del greenlet async al serializar.
    await session.refresh(sesion, attribute_names=["carga_srpe"])

    # Molestias del mismo dia que la sesion.
    molestias = await repo_molestia.listar_por_usuario_y_fecha(
        session, sesion.usuario_id, sesion.fecha
    )

    # Emparejar bloques reales con bloques planeados por orden. Si el
    # usuario agrego bloques que no estaban en el plan, quedan con
    # `bloque_plan=None` y delta todo NULL.
    plan = sesion.sesion_plan
    bloques_planeados_por_orden: dict[int, BloquePlan] = (
        {bp.orden: bp for bp in plan.bloques_planeados}
        if plan is not None and plan.bloques_planeados
        else {}
    )
    bloques_detalle = [
        _armar_bloque_detalle(bloque, bloques_planeados_por_orden.get(bloque.orden))
        for bloque in sorted(sesion.bloques, key=lambda b: b.orden)
    ]
    bloques_no_ejecutados: list[BloqueNoEjecutadoRead] = []
    if plan is not None and plan.bloques_planeados:
        ordenes_ejecutados = {b.orden for b in sesion.bloques}
        for bp in plan.bloques_planeados:
            if bp.orden not in ordenes_ejecutados:
                bloques_no_ejecutados.append(
                    BloqueNoEjecutadoRead(
                        orden=bp.orden,
                        ejercicio_id=bp.ejercicio_id,
                        ejercicio_nombre=bp.ejercicio.nombre,
                        objetivo=_armar_objetivo(bp),  # type: ignore[arg-type]
                    )
                )

    # Delta de sesion: solo si tiene plan (sin plan → None, no un
    # `SesionDeltaRead` con campos NULL).
    delta_read: SesionDeltaRead | None = None
    if plan is not None:
        resultado_sesion = delta_sesion(
            real=SesionDeltaInput(
                duracion_min=sesion.duracion_min,
                rpe=sesion.rpe,
                carga_srpe=sesion.carga_srpe,
            ),
            plan=SesionPlanDeltaInput(
                duracion_min_est=plan.duracion_min_est,
                rpe_objetivo=plan.rpe_objetivo,
            ),
        )
        if resultado_sesion is not None:
            delta_read = SesionDeltaRead(
                duracion_min=resultado_sesion.duracion_min,
                rpe=resultado_sesion.rpe,
                carga_srpe=resultado_sesion.carga_srpe,
            )

    return SesionDetalleRead(
        id=sesion.id,
        usuario_id=sesion.usuario_id,
        sesion_plan_id=sesion.sesion_plan_id,
        fecha=sesion.fecha,
        tipo_sesion=SesionTipoRead(
            id=sesion.tipo_sesion.id,
            codigo=sesion.tipo_sesion.codigo,
            nombre=sesion.tipo_sesion.nombre,
        ),
        duracion_min=sesion.duracion_min,
        rpe=sesion.rpe,
        nota=sesion.nota,
        carga_srpe=sesion.carga_srpe,
        registrado_en=sesion.registrado_en,
        plan=_armar_plan_detalle(sesion),
        delta=delta_read,
        bloques=bloques_detalle,
        bloques_no_ejecutados=bloques_no_ejecutados,
        molestias=[
            MolestiaDetalleRead(zona=m.zona.nombre, intensidad=m.intensidad)
            for m in molestias
        ],
    )


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
            nota=b.nota,
        )

    # La fecha pudo moverse: cumplido <-> movido se recalcula.
    if sesion.sesion_plan_id is not None:
        await resolver_estado_de_plan(session, sesion.sesion_plan_id)

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
    sesion_plan_id = sesion.sesion_plan_id
    await repo.eliminar_sesion(session, sesion)
    # Sin sesion real el plan vuelve a pendiente (o sigue descartado). Va
    # despues del DELETE: resolver_estado_de_plan busca la sesion asociada y
    # tiene que no encontrarla.
    if sesion_plan_id is not None:
        await resolver_estado_de_plan(session, sesion_plan_id)
    await session.commit()
