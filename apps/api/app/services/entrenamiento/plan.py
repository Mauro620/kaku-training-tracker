"""Orquestación de sesion_plan: crea validando el espaciado (REGLAS_NEGOCIO
§13.3) cuando el plan trae `dia_sugerido`."""

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvarianteDeNegocioError, RecursoNoEncontradoError
from app.models import CicloSemana, SesionPlan
from app.models.enums import EstadoSesionPlan
from app.repositories import entrenamiento as repo
from app.repositories.entrenamiento import plan as repo_plan
from app.schemas.entrenamiento.plan import (
    BloquePlanDetalleRead,
    PlanCicloRead,
    PlanDetalleRead,
    SesionPlanCreate,
)
from app.schemas.entrenamiento.sesion import BloqueEjercicioEnDetalleRead
from app.services.entrenamiento.bloque import validar_campos
from app.services.entrenamiento.ciclo import (
    calcular_rango_semana,
    obtener_ciclo,
    obtener_semana,
)
from app.services.entrenamiento.espaciado import validar_espaciado


async def crear_sesion_plan(
    session: AsyncSession, usuario_id: uuid.UUID, payload: SesionPlanCreate
) -> SesionPlan:
    ciclo = None
    if payload.ciclo_semana_id is not None:
        semana = await obtener_semana(session, usuario_id, payload.ciclo_semana_id)
        ciclo = await obtener_ciclo(session, usuario_id, semana.ciclo_id)

        tipos = {t.id: t for t in await repo.listar_tipos_sesion(session)}
        tipo_sesion = tipos.get(payload.tipo_sesion_id)
        if tipo_sesion is None:
            raise RecursoNoEncontradoError(
                f"tipo_sesion {payload.tipo_sesion_id} no encontrado"
            )

        await validar_espaciado(
            session,
            usuario_id=usuario_id,
            ciclo=ciclo,
            semana=semana,
            tipo_sesion=tipo_sesion,
            dia_sugerido=payload.dia_sugerido,
        )

    bloques_payload = payload.bloques or []
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
            reps=b.reps_min if b.reps_min is not None else b.reps_max,
            peso=b.peso_objetivo_kg,
            distancia=b.distancia_objetivo_m,
            duracion=b.duracion_objetivo_s,
        )

    plan = await repo.crear_sesion_plan(
        session,
        usuario_id=usuario_id,
        ciclo_semana_id=payload.ciclo_semana_id,
        tipo_sesion_id=payload.tipo_sesion_id,
        fecha_prevista=payload.fecha_prevista,
        dia_sugerido=payload.dia_sugerido,
        objetivo=payload.objetivo,
        duracion_min_est=payload.duracion_min_est,
        rpe_objetivo=payload.rpe_objetivo,
    )
    for idx, b in enumerate(bloques_payload):
        await repo.crear_bloque_plan(
            session,
            sesion_plan_id=plan.id,
            ejercicio_id=b.ejercicio_id,
            orden=idx + 1,
            series=b.series,
            reps_min=b.reps_min,
            reps_max=b.reps_max,
            peso_objetivo_kg=b.peso_objetivo_kg,
            distancia_objetivo_m=b.distancia_objetivo_m,
            duracion_objetivo_s=b.duracion_objetivo_s,
        )

    await session.commit()
    # attribute_names: SesionPlanRead siempre incluye bloques_planeados, asi
    # que el service es quien los deja cargados antes de devolver.
    await session.refresh(plan, attribute_names=["bloques_planeados"])
    return plan


async def listar_planes_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[SesionPlan]:
    """Planes "de hoy" (ROADMAP §4): `fecha_prevista` exacta, o `dia_sugerido`
    que cae en `fecha` una vez resuelto contra el ciclo. El repo ya acota por
    rango del ciclo; acá se resuelve el dia exacto, que necesita
    `ciclo_semana.numero` y por eso no se puede hacer en una sola query."""
    candidatos = await repo.listar_planes_candidatos_de_fecha(
        session, usuario_id, fecha
    )
    semanas_cache: dict[int, CicloSemana | None] = {}
    resultado = []
    for plan in candidatos:
        if plan.fecha_prevista == fecha:
            resultado.append(plan)
            continue
        if plan.dia_sugerido is None or plan.ciclo_semana_id is None:
            continue
        if plan.ciclo_semana_id not in semanas_cache:
            semanas_cache[
                plan.ciclo_semana_id
            ] = await repo.obtener_ciclo_semana_por_id(session, plan.ciclo_semana_id)
        semana = semanas_cache[plan.ciclo_semana_id]
        if semana is None:
            continue
        ciclo = await obtener_ciclo(session, usuario_id, semana.ciclo_id)
        inicio_semana, _ = calcular_rango_semana(ciclo.fecha_inicio, semana.numero)
        if inicio_semana + timedelta(days=plan.dia_sugerido) == fecha:
            resultado.append(plan)
    return resultado


async def resolver_estado_de_plan(session: AsyncSession, sesion_plan_id: int) -> None:
    """Recalcula `sesion_plan.estado` a partir de la sesión real asociada.

    El estado se PERSISTE en vez de derivarse al leer, así que esta función
    es la única que lo escribe y hay que llamarla desde TODO camino que cree,
    mueva de fecha o borre una `sesion` (ver `services/entrenamiento/sesion.py`).
    Si aparece un camino nuevo que toque `sesion.fecha` o `sesion.sesion_plan_id`
    sin pasar por acá, la columna miente y el importador pisa histórico.

    No commitea: la deja preparada para el commit de quien la llamó.
    """
    plan = await repo.obtener_sesion_plan_por_id(session, sesion_plan_id)
    if plan is None:
        return

    sesion = await repo.obtener_sesion_por_plan(session, sesion_plan_id)
    if sesion is None:
        # `descartado` lo declaró el usuario: no se pisa por no haber sesión,
        # que es justamente lo que descartar significa.
        nuevo = (
            EstadoSesionPlan.descartado
            if plan.estado is EstadoSesionPlan.descartado
            else EstadoSesionPlan.pendiente
        )
    elif plan.dia_sugerido is None or plan.ciclo_semana_id is None:
        # Sin día planeado no hay contra qué comparar: se ejecutó y ya.
        # Ejecutar gana sobre descartar: el entrenamiento pasó de verdad.
        nuevo = EstadoSesionPlan.cumplido
    else:
        semana = await repo.obtener_ciclo_semana_por_id(session, plan.ciclo_semana_id)
        assert semana is not None  # FK garantiza que existe
        ciclo = await repo.obtener_ciclo_por_id(session, semana.ciclo_id)
        assert ciclo is not None  # FK garantiza que existe
        inicio_semana, _ = calcular_rango_semana(ciclo.fecha_inicio, semana.numero)
        nuevo = (
            EstadoSesionPlan.cumplido
            if (sesion.fecha - inicio_semana).days == plan.dia_sugerido
            else EstadoSesionPlan.movido
        )

    if plan.estado is not nuevo:
        await repo.actualizar_estado_sesion_plan(session, plan, nuevo)


async def recuperar_plan(
    session: AsyncSession, usuario_id: uuid.UUID, sesion_plan_id: int
) -> SesionPlan:
    """Deshace un descarte: el plan vuelve a `pendiente`.

    Descartar es una decision del usuario y, como cualquiera, se puede
    equivocar: sin esto un plan descartado por un toque accidental no tenia
    vuelta atras. Solo aplica a `descartado`; un plan `cumplido` o `movido` lo
    resuelve el sistema contra la sesion real y no se toca a mano.

    Pasa por `resolver_estado_de_plan` y no escribe `pendiente` a ciegas: si el
    plan tuviera una sesion real, `ejecutar gana` y queda cumplido/movido.
    """
    plan = await repo.obtener_sesion_plan_por_id(session, sesion_plan_id)
    if plan is None or plan.usuario_id != usuario_id:
        raise RecursoNoEncontradoError(f"sesion_plan {sesion_plan_id} no encontrado")
    if plan.estado is not EstadoSesionPlan.descartado:
        raise InvarianteDeNegocioError(
            "Solo se puede recuperar un plan descartado "
            f"(este esta {plan.estado.value})."
        )
    # Se saca de `descartado` primero: el resolver respeta ese estado cuando no
    # hay sesion, y justamente eso es lo que se quiere deshacer.
    await repo.actualizar_estado_sesion_plan(session, plan, EstadoSesionPlan.pendiente)
    await resolver_estado_de_plan(session, plan.id)
    await session.commit()
    await session.refresh(plan, attribute_names=["bloques_planeados"])
    return plan


async def descartar_plan(
    session: AsyncSession, usuario_id: uuid.UUID, sesion_plan_id: int
) -> SesionPlan:
    """El usuario declara que un plan no se va a hacer. Es la única
    transición de estado que elige una persona: `cumplido` y `movido` los
    resuelve `resolver_estado_de_plan` contra la sesión real."""
    plan = await repo.obtener_sesion_plan_por_id(session, sesion_plan_id)
    if plan is None or plan.usuario_id != usuario_id:
        raise RecursoNoEncontradoError(f"sesion_plan {sesion_plan_id} no encontrado")
    if plan.estado in (EstadoSesionPlan.cumplido, EstadoSesionPlan.movido):
        raise InvarianteDeNegocioError(
            "El plan ya se ejecutó: no se puede descartar. El histórico no se toca."
        )
    await repo.actualizar_estado_sesion_plan(session, plan, EstadoSesionPlan.descartado)
    await session.commit()
    await session.refresh(plan, attribute_names=["bloques_planeados"])
    return plan


async def obtener_plan_detalle(
    session: AsyncSession, usuario_id: uuid.UUID, plan_id: int
) -> PlanDetalleRead:
    """Detalle de un plan (R9, SPEC §3.8): cabecera + ciclo anidado
    opcional + bloques planeados ordenados por `orden` ASC, cada uno con
    su ejercicio. 404 si el plan no existe o no es del usuario (no se
    filtra la existencia para no distinguir entre "no existe" y "no es
    tuyo", AGENTS §5)."""
    plan = await repo_plan.obtener_con_detalle(session, plan_id)
    if plan is None or plan.usuario_id != usuario_id:
        raise RecursoNoEncontradoError(f"sesion_plan {plan_id} no encontrado")

    ciclo = None
    if plan.ciclo_semana is not None and plan.ciclo_semana.ciclo is not None:
        ciclo = PlanCicloRead(
            numero=plan.ciclo_semana.ciclo.numero,
            semana=plan.ciclo_semana.numero,
            fase=plan.ciclo_semana.fase,
        )

    # `SesionPlan.bloques_planeados` ya viene ordenado por `orden` ASC via
    # `order_by="BloquePlan.orden"` en la relación; el `sorted` es defensa
    # por si alguien cambia esa configuración en el modelo.
    bloques = [
        BloquePlanDetalleRead(
            id=bp.id,
            sesion_plan_id=bp.sesion_plan_id,
            orden=bp.orden,
            series=bp.series,
            reps_min=bp.reps_min,
            reps_max=bp.reps_max,
            peso_objetivo_kg=bp.peso_objetivo_kg,
            distancia_objetivo_m=bp.distancia_objetivo_m,
            duracion_objetivo_s=bp.duracion_objetivo_s,
            nota=bp.nota,
            ejercicio=BloqueEjercicioEnDetalleRead(
                id=bp.ejercicio.id,
                nombre=bp.ejercicio.nombre,
                tipo_medicion=bp.ejercicio.tipo_medicion,
                descripcion=bp.ejercicio.descripcion,
                carga_lumbar=bp.ejercicio.carga_lumbar,
            ),
        )
        for bp in sorted(plan.bloques_planeados, key=lambda b: b.orden)
    ]

    return PlanDetalleRead(
        id=plan.id,
        usuario_id=plan.usuario_id,
        ciclo_semana_id=plan.ciclo_semana_id,
        ciclo=ciclo,
        fecha_prevista=plan.fecha_prevista,
        dia_sugerido=plan.dia_sugerido,
        tipo_sesion_id=plan.tipo_sesion_id,
        objetivo=plan.objetivo,
        duracion_min_est=plan.duracion_min_est,
        rpe_objetivo=plan.rpe_objetivo,
        estado=plan.estado,
        clave_import=plan.clave_import,
        nombre=plan.nombre,
        nota=plan.nota,
        bloques_planeados=bloques,
    )
