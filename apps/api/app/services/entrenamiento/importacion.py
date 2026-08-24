"""Importacion de la planificacion de una semana completa desde un JSON.

Planear es trabajo de escritorio; registrar es trabajo de campo. Este modulo
existe para que el domingo se cargue la semana entera de una sola vez y en la
cancha solo haya que confirmar numeros sobre filas que ya existen
(docs/feature_1_session_plan_json/PLAN_IMPORT.md).

Dos invariantes gobiernan todo lo de abajo:

1. **El historico es intocable.** Un plan en `cumplido` o `movido` nunca se
   reemplaza: se omite y se reporta. Reimportar corrige el futuro, no reescribe
   el pasado.
2. **Nada se sobrescribe en el catalogo.** Un ejercicio que ya existe conserva
   su `tipo_medicion`; cambiarselo invalidaria los bloques historicos que se
   midieron con el anterior.
"""

import uuid
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvarianteDeNegocioError
from app.models import Ciclo, CicloSemana, Ejercicio, SesionPlan, TipoSesion
from app.models.enums import EstadoSesionPlan
from app.repositories import entrenamiento as repo
from app.schemas.entrenamiento.importacion import (
    ImportacionResultado,
    PlanSemanalImport,
    SesionImport,
)
from app.services.entrenamiento.bloque import validar_campos
from app.services.entrenamiento.espaciado import evaluar_espaciado
from app.services.entrenamiento.plan import resolver_estado_de_plan

ESTADOS_EJECUTADOS = (EstadoSesionPlan.cumplido, EstadoSesionPlan.movido)


async def importar_plan_semanal(
    session: AsyncSession, usuario_id: uuid.UUID, payload: PlanSemanalImport
) -> ImportacionResultado:
    tipos = await _resolver_tipos(session, payload)
    ejercicios, ejercicios_creados = await _resolver_ejercicios(session, payload)
    _validar_bloques(payload, ejercicios)

    ciclo = await _resolver_ciclo(session, usuario_id, payload)
    semana = await _resolver_semana(session, ciclo, payload)

    ejecutadas, previas, advertencias = await _liberar_claves(session, semana, payload)

    creadas = 0
    reemplazadas = 0
    advertencias_espaciado: list[str] = []

    # En orden de dia y no en orden del JSON: `evaluar_espaciado` compara
    # contra los planes que YA existen en la base, asi que crear de lunes a
    # domingo hace que cada conflicto se reporte una sola vez (el del dia
    # posterior ve al anterior; el anterior no ve al que todavia no existe).
    for sesion_json in sorted(payload.sesiones, key=lambda s: s.dia):
        if sesion_json.clave_import in ejecutadas:
            continue
        tipo_sesion = tipos[sesion_json.tipo]
        advertencias_espaciado.extend(
            await evaluar_espaciado(
                session,
                usuario_id=usuario_id,
                ciclo=ciclo,
                semana=semana,
                tipo_sesion=tipo_sesion,
                dia_sugerido=sesion_json.dia,
            )
        )
        await _crear_plan(
            session, usuario_id, semana, sesion_json, tipo_sesion, ejercicios
        )
        if sesion_json.clave_import in previas:
            reemplazadas += 1
        else:
            creadas += 1

    await _reemplazar_composicion(session, semana, payload, tipos)
    await session.commit()

    # dict.fromkeys y no set: preserva el orden y saca el duplicado exacto que
    # aparece cuando un plan ya ejecutado figura a la vez como plan y como
    # sesion real dentro del mismo rango.
    advertencias.extend(dict.fromkeys(advertencias_espaciado))
    if ejercicios_creados:
        advertencias.append(
            "Se crearon ejercicios nuevos en el catalogo: "
            + ", ".join(ejercicios_creados)
        )

    return ImportacionResultado(
        ciclo_id=ciclo.id,
        ciclo_semana_id=semana.id,
        sesiones_creadas=creadas,
        sesiones_reemplazadas=reemplazadas,
        sesiones_omitidas=len(ejecutadas),
        ejercicios_creados=ejercicios_creados,
        advertencias=advertencias,
    )


async def _resolver_tipos(
    session: AsyncSession, payload: PlanSemanalImport
) -> dict[str, TipoSesion]:
    """`tipo_sesion` es catalogo sembrado: un codigo que no esta es un error
    del JSON, no algo para crear al vuelo."""
    catalogo = {t.codigo: t for t in await repo.listar_tipos_sesion(session)}
    desconocidos = sorted({s.tipo for s in payload.sesiones} - catalogo.keys())
    if desconocidos:
        raise InvarianteDeNegocioError(
            "tipo de sesion desconocido: "
            + ", ".join(desconocidos)
            + ". Validos: "
            + ", ".join(sorted(catalogo))
        )
    return catalogo


async def _resolver_ejercicios(
    session: AsyncSession, payload: PlanSemanalImport
) -> tuple[dict[str, Ejercicio], list[str]]:
    """Busca o crea cada ejercicio por nombre. NUNCA sobrescribe uno existente:
    si el JSON declara otro `tipo_medicion` para un ejercicio que ya esta en el
    catalogo, se rechaza la importacion entera. Cambiar el tipo invalidaria los
    bloques historicos medidos con el anterior (PLAN_IMPORT.md 6)."""
    resueltos: dict[str, Ejercicio] = {}
    creados: list[str] = []
    conflictos: list[str] = []

    for sesion_json in payload.sesiones:
        for bloque in sesion_json.bloques:
            if bloque.ejercicio in resueltos:
                existente = resueltos[bloque.ejercicio]
                if existente.tipo_medicion is not bloque.tipo_medicion:
                    conflictos.append(
                        f"{bloque.ejercicio}: el JSON lo declara como "
                        f"{bloque.tipo_medicion.value} y como "
                        f"{existente.tipo_medicion.value}"
                    )
                continue

            ejercicio = await repo.obtener_ejercicio_por_nombre(
                session, bloque.ejercicio
            )
            if ejercicio is None:
                ejercicio = await repo.crear_ejercicio(
                    session, nombre=bloque.ejercicio, tipo_medicion=bloque.tipo_medicion
                )
                creados.append(bloque.ejercicio)
            elif ejercicio.tipo_medicion is not bloque.tipo_medicion:
                conflictos.append(
                    f"{bloque.ejercicio}: ya existe con tipo_medicion="
                    f"{ejercicio.tipo_medicion.value}, el JSON declara "
                    f"{bloque.tipo_medicion.value}"
                )
            resueltos[bloque.ejercicio] = ejercicio

    if conflictos:
        raise InvarianteDeNegocioError(
            "un ejercicio existente no cambia de tipo_medicion: "
            + "; ".join(conflictos)
        )
    return resueltos, creados


def _validar_bloques(
    payload: PlanSemanalImport, ejercicios: dict[str, Ejercicio]
) -> None:
    """Misma regla que un bloque real (REGLAS_NEGOCIO 15), contra el
    `tipo_medicion` que quedo en el catalogo, no contra el que declaro el JSON:
    para un ejercicio nuevo son el mismo, y para uno existente el catalogo
    manda."""
    for sesion_json in payload.sesiones:
        for bloque in sesion_json.bloques:
            reps_min, reps_max = bloque.rango_reps
            validar_campos(
                ejercicios[bloque.ejercicio].tipo_medicion,
                ejercicio_nombre=bloque.ejercicio,
                series=bloque.series,
                reps=reps_min if reps_min is not None else reps_max,
                peso=bloque.peso_kg,
                distancia=bloque.distancia_m,
                duracion=bloque.duracion_s,
            )


async def _resolver_ciclo(
    session: AsyncSession, usuario_id: uuid.UUID, payload: PlanSemanalImport
) -> Ciclo:
    """Busca por `numero` o crea. Un ciclo que ya existe NO se redefine: su
    `fecha_inicio` es de donde sale el rango de fechas de todas sus semanas, y
    moverla desde la importacion de una sola semana correria el calendario de
    sesiones que ya se registraron."""
    ciclo = await repo.obtener_ciclo_por_numero(
        session, usuario_id, payload.ciclo.numero
    )
    if ciclo is not None:
        return ciclo
    return await repo.crear_ciclo(
        session,
        usuario_id=usuario_id,
        numero=payload.ciclo.numero,
        objetivo=payload.ciclo.objetivo,
        fecha_inicio=payload.ciclo.fecha_inicio,
        semanas=payload.ciclo.semanas,
    )


async def _resolver_semana(
    session: AsyncSession, ciclo: Ciclo, payload: PlanSemanalImport
) -> CicloSemana:
    """Busca por `numero` o crea. A diferencia del ciclo, la semana SI se
    actualiza: fase, RPE objetivo y volumen son exactamente lo que se esta
    replanificando. `numero` no se toca, es su identidad."""
    rpe = payload.semana.rpe_objetivo
    semana = await repo.obtener_ciclo_semana_por_numero(
        session, ciclo.id, payload.semana.numero
    )
    if semana is None:
        return await repo.crear_ciclo_semana(
            session,
            ciclo_id=ciclo.id,
            numero=payload.semana.numero,
            fase=payload.semana.fase,
            rpe_objetivo_min=rpe.min if rpe else None,
            rpe_objetivo_max=rpe.max if rpe else None,
            volumen_pct=payload.semana.volumen_pct,
        )
    return await repo.actualizar_ciclo_semana(
        session,
        semana,
        fase=payload.semana.fase,
        rpe_objetivo_min=rpe.min if rpe else None,
        rpe_objetivo_max=rpe.max if rpe else None,
        volumen_pct=payload.semana.volumen_pct,
    )


async def _liberar_claves(
    session: AsyncSession, semana: CicloSemana, payload: PlanSemanalImport
) -> tuple[set[str], set[str], list[str]]:
    """Borra los planes importados que el JSON vuelve a traer, para que se
    recreen limpios.

    Devuelve `(ejecutadas, previas, advertencias)`: las claves que NO se pueden
    tocar, las que ya existian en la semana (para distinguir un plan creado de
    uno reemplazado) y los avisos de lo que se conservo.

    Se recalcula el estado de cada plan antes de decidir: la columna es la
    fuente de verdad, y recalcularla acá cierra la ventana en la que un camino
    que no llamo a `resolver_estado_de_plan` la dejo mintiendo. Sin esto, un
    plan con sesion real pero marcado `pendiente` se borraria y el DELETE
    reventaria contra la FK de `sesion`.
    """
    claves = [s.clave_import for s in payload.sesiones]
    existentes = await repo.listar_planes_por_semana_y_claves(
        session, semana.id, claves
    )

    ejecutadas: set[str] = set()
    previas: set[str] = set()
    advertencias: list[str] = []

    for plan in existentes:
        assert plan.clave_import is not None  # vino filtrado por clave_import
        previas.add(plan.clave_import)
        await resolver_estado_de_plan(session, plan.id)
        await session.refresh(plan, attribute_names=["estado"])
        if plan.estado in ESTADOS_EJECUTADOS:
            ejecutadas.add(plan.clave_import)
            advertencias.append(
                f"El plan {plan.clave_import} ya se ejecuto "
                f"({plan.estado.value}): se conserva el original y se ignora "
                f"lo que trae el JSON."
            )
            continue
        await _eliminar_plan(session, plan)

    return ejecutadas, previas, advertencias


async def _eliminar_plan(session: AsyncSession, plan: SesionPlan) -> None:
    await repo.eliminar_bloques_de_plan(session, plan.id)
    await repo.eliminar_sesion_plan(session, plan)


async def _crear_plan(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    semana: CicloSemana,
    sesion_json: SesionImport,
    tipo_sesion: TipoSesion,
    ejercicios: dict[str, Ejercicio],
) -> SesionPlan:
    plan = await repo.crear_sesion_plan(
        session,
        usuario_id=usuario_id,
        ciclo_semana_id=semana.id,
        tipo_sesion_id=tipo_sesion.id,
        # fecha_prevista queda NULL: el dia se resuelve contra el rango del
        # ciclo (REGLAS_NEGOCIO 13.1), no se congela en una fecha que quedaria
        # desalineada si `ciclo.fecha_inicio` se corrige.
        fecha_prevista=None,
        dia_sugerido=sesion_json.dia,
        objetivo=sesion_json.objetivo,
        duracion_min_est=sesion_json.duracion_min,
        rpe_objetivo=sesion_json.rpe_objetivo,
        clave_import=sesion_json.clave_import,
    )
    for orden, bloque in enumerate(sesion_json.bloques, start=1):
        reps_min, reps_max = bloque.rango_reps
        await repo.crear_bloque_plan(
            session,
            sesion_plan_id=plan.id,
            ejercicio_id=ejercicios[bloque.ejercicio].id,
            orden=orden,
            series=bloque.series,
            reps_min=reps_min,
            reps_max=reps_max,
            peso_objetivo_kg=bloque.peso_kg,
            distancia_objetivo_m=bloque.distancia_m,
            duracion_objetivo_s=bloque.duracion_s,
        )
    return plan


async def _reemplazar_composicion(
    session: AsyncSession,
    semana: CicloSemana,
    payload: PlanSemanalImport,
    tipos: dict[str, TipoSesion],
) -> None:
    """La composicion no se declara, se deriva de las sesiones del JSON
    (PLAN_IMPORT.md 3). Declararla aparte abre la puerta a que no coincida con
    las sesiones que realmente se planificaron."""
    conteo = Counter(s.tipo for s in payload.sesiones)
    await repo.reemplazar_composicion(
        session,
        semana.id,
        [(tipos[codigo].id, cantidad) for codigo, cantidad in sorted(conteo.items())],
    )
