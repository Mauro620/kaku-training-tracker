"""Las cuatro preguntas de Progreso (REGLAS_NEGOCIO §18). Solo lectura."""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TestFisico, TipoTest, Usuario
from app.models.enums import EstadoSesionPlan, TipoMedicion
from app.repositories import entrenamiento as repo_entrenamiento
from app.repositories import metricas as repo
from app.schemas.metricas.progreso import (
    BandasAcwr,
    ComposicionRead,
    CumplimientoRead,
    MejorMarca,
    PruebaTendencia,
    PuntoPrueba,
    RecuperacionRead,
    RendimientoRead,
    SemanaComposicion,
    SemanaCumplimiento,
    SemanaRecuperacion,
)
from app.services.catalogo import parametro as parametros
from app.services.entrenamiento.ciclo import calcular_rango_semana
from app.services.evaluacion.calculo import calcular_pct_cambio, mejor_intento
from app.services.metricas import conclusiones
from app.services.metricas.calculo import (
    calcular_acwr,
    clasificar_acwr,
    e1rm_epley,
    porcentaje,
    promedio,
    redondear,
)


async def _param(session: AsyncSession, clave: str) -> Decimal:
    return (await parametros.obtener(session, clave)).valor


def _lunes(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


# ------------------------------------------------------ 1. ¿Cumpli el plan? --


async def cumplimiento(
    session: AsyncSession, usuario_id: uuid.UUID, hoy: date
) -> CumplimientoRead:
    ciclo = await repo.ciclo_resumible(session, usuario_id)
    if ciclo is None:
        return CumplimientoRead(
            ciclo_numero=None,
            semanas=[],
            conclusion=conclusiones.cumplimiento([]),
        )
    semanas = await repo_entrenamiento.listar_ciclo_semanas_por_ciclo(session, ciclo.id)
    planes = await repo.planes_del_ciclo(session, ciclo.id)
    corte = min(hoy, ciclo.fecha_cierre_real or ciclo.fecha_fin_prevista)

    salida: list[SemanaCumplimiento] = []
    for semana in semanas:
        inicio, fin = calcular_rango_semana(ciclo.fecha_inicio, semana.numero)
        if inicio > corte:
            continue
        estados = [p.estado for p, _t, n in planes if n == semana.numero]
        total = len(estados)

        def n(e: EstadoSesionPlan, estados: list[EstadoSesionPlan] = estados) -> int:
            return estados.count(e)

        cumplido = n(EstadoSesionPlan.cumplido)
        movido = n(EstadoSesionPlan.movido)
        descartado = n(EstadoSesionPlan.descartado)
        pendiente = n(EstadoSesionPlan.pendiente)
        salida.append(
            SemanaCumplimiento(
                numero=semana.numero,
                inicio=inicio,
                fin=fin,
                planeadas=total,
                cumplido=cumplido,
                movido=movido,
                descartado=descartado,
                pendiente=pendiente,
                pct_cumplido=porcentaje(cumplido, total),
                pct_movido=porcentaje(movido, total),
                pct_descartado=porcentaje(descartado, total),
                pct_pendiente=porcentaje(pendiente, total),
            )
        )
    return CumplimientoRead(
        ciclo_numero=ciclo.numero,
        semanas=salida,
        conclusion=conclusiones.cumplimiento(salida),
    )


# ------------------------------------------------ 2. ¿Estoy rindiendo mejor? --


async def rendimiento(
    session: AsyncSession, usuario_id: uuid.UUID, hoy: date
) -> RendimientoRead:
    historico = await repo.tests_con_tipo_hasta(session, usuario_id, hoy)
    por_tipo: dict[int, list[tuple[TestFisico, TipoTest]]] = defaultdict(list)
    for test, tipo in historico:
        por_tipo[tipo.id].append((test, tipo))

    pruebas: list[PruebaTendencia] = []
    for filas in por_tipo.values():
        tipo = filas[0][1]
        base_test = filas[0][0]
        base = mejor_intento([i.valor for i in base_test.intentos], tipo.mejor_es_mayor)
        puntos = []
        for test, _ in filas:
            mejor = mejor_intento([i.valor for i in test.intentos], tipo.mejor_es_mayor)
            puntos.append(
                PuntoPrueba(
                    fecha=test.fecha,
                    mejor=float(mejor),
                    pct_cambio_vs_base=(
                        None
                        if test.id == base_test.id
                        else float(
                            calcular_pct_cambio(base, mejor, tipo.mejor_es_mayor)
                        )
                    ),
                )
            )
        pruebas.append(
            PruebaTendencia(
                codigo=tipo.codigo,
                nombre=tipo.nombre,
                unidad=tipo.unidad,
                mejor_es_mayor=tipo.mejor_es_mayor,
                puntos=puntos,
            )
        )

    marcas = await _mejores_marcas(session, usuario_id)
    return RendimientoRead(
        pruebas=pruebas,
        marcas=marcas,
        conclusion=conclusiones.rendimiento(pruebas, len(marcas)),
    )


async def _mejores_marcas(
    session: AsyncSession, usuario_id: uuid.UUID
) -> list[MejorMarca]:
    divisor = await _param(session, "epley_divisor")
    reps_max = int(await _param(session, "epley_reps_max"))

    marcas: dict[int, MejorMarca] = {}
    for bloque, ejercicio, fecha in await repo.bloques_reales(session, usuario_id):
        tipo = ejercicio.tipo_medicion
        # Valor comparable del bloque segun su tipo; None = no aporta marca.
        if tipo is TipoMedicion.carga:
            if bloque.peso_kg is None:
                continue
            rm = (
                e1rm_epley(bloque.peso_kg, bloque.reps, divisor=divisor)
                if bloque.reps is not None and bloque.reps <= reps_max
                else None
            )
            candidato = MejorMarca(
                ejercicio_id=ejercicio.id,
                ejercicio=ejercicio.nombre,
                tipo_medicion=tipo.value,
                peso_max_kg=float(bloque.peso_kg),
                rm_estimado_kg=redondear(rm) if rm is not None else None,
                fecha=fecha,
            )
        elif tipo is TipoMedicion.tiempo and bloque.duracion_s:
            candidato = MejorMarca(
                ejercicio_id=ejercicio.id,
                ejercicio=ejercicio.nombre,
                tipo_medicion=tipo.value,
                duracion_max_s=bloque.duracion_s,
                fecha=fecha,
            )
        elif tipo is TipoMedicion.distancia and bloque.distancia_m:
            candidato = MejorMarca(
                ejercicio_id=ejercicio.id,
                ejercicio=ejercicio.nombre,
                tipo_medicion=tipo.value,
                distancia_max_m=float(bloque.distancia_m),
                fecha=fecha,
            )
        elif tipo is TipoMedicion.tecnica and bloque.calidad:
            candidato = MejorMarca(
                ejercicio_id=ejercicio.id,
                ejercicio=ejercicio.nombre,
                tipo_medicion=tipo.value,
                calidad_max=bloque.calidad,
                fecha=fecha,
            )
        else:
            continue
        previa = marcas.get(ejercicio.id)
        marcas[ejercicio.id] = (
            candidato if previa is None else _mejor(previa, candidato)
        )
    return sorted(marcas.values(), key=lambda m: m.ejercicio)


def _mejor(a: MejorMarca, b: MejorMarca) -> MejorMarca:
    """Combina dos marcas del mismo ejercicio: el maximo de cada campo, con la
    fecha de la sesion que lo dejo mas arriba (la ultima si empatan)."""

    def maximo(x: float | None, y: float | None) -> float | None:
        if x is None or y is None:
            return x if y is None else y
        return max(x, y)

    def fecha_de(campo: str) -> date:
        va, vb = getattr(a, campo), getattr(b, campo)
        if va is None or vb is None or vb >= va:
            return b.fecha
        return a.fecha

    campo = {
        "carga": "peso_max_kg",
        "tiempo": "duracion_max_s",
        "distancia": "distancia_max_m",
        "tecnica": "calidad_max",
    }[a.tipo_medicion]
    return a.model_copy(
        update={
            "peso_max_kg": maximo(a.peso_max_kg, b.peso_max_kg),
            "rm_estimado_kg": maximo(a.rm_estimado_kg, b.rm_estimado_kg),
            "duracion_max_s": (
                int(m) if (m := maximo(a.duracion_max_s, b.duracion_max_s)) else None
            ),
            "distancia_max_m": maximo(a.distancia_max_m, b.distancia_max_m),
            "calidad_max": (
                int(m) if (m := maximo(a.calidad_max, b.calidad_max)) else None
            ),
            "fecha": fecha_de(campo),
        }
    )


# ------------------------------------------------- 3. ¿Me estoy recuperando? --


async def recuperacion(
    session: AsyncSession, usuario_id: uuid.UUID, hoy: date, semanas: int
) -> RecuperacionRead:
    dias_agudo = int(await _param(session, "acwr_dias_agudo"))
    dias_cronico = int(await _param(session, "acwr_dias_cronico"))
    bandas = BandasAcwr(
        min_seguro=float(await _param(session, "acwr_min_seguro")),
        max_seguro=float(await _param(session, "acwr_max_seguro")),
        alerta=float(await _param(session, "acwr_umbral_alerta")),
    )
    objetivo_sueno = float(await _param(session, "sueno_objetivo_horas"))

    primer_lunes = _lunes(hoy) - timedelta(weeks=semanas - 1)
    # El ACWR de la primera semana mira 28 dias hacia atras.
    carga = await repo.carga_diaria(
        session, usuario_id, primer_lunes - timedelta(days=dias_cronico), hoy
    )
    primera = await repo.primera_fecha_de_sesion(session, usuario_id)
    sueno = await repo.sueno_en_rango(session, usuario_id, primer_lunes, hoy)

    salida: list[SemanaRecuperacion] = []
    for k in range(semanas):
        inicio = primer_lunes + timedelta(weeks=k)
        fin = inicio + timedelta(days=6)
        corte = min(fin, hoy)
        acwr = calcular_acwr(
            carga, corte, primera, dias_agudo=dias_agudo, dias_cronico=dias_cronico
        )
        horas = [h for f, h in sueno if inicio <= f <= corte]
        salida.append(
            SemanaRecuperacion(
                inicio=inicio,
                fin=fin,
                en_curso=fin > hoy,
                carga_semanal=sum(
                    carga.get(inicio + timedelta(days=d), 0) for d in range(7)
                ),
                acwr=acwr,
                semaforo=clasificar_acwr(
                    acwr,
                    min_seguro=bandas.min_seguro,
                    max_seguro=bandas.max_seguro,
                    alerta=bandas.alerta,
                ),
                sueno_prom_h=promedio(horas),
                sueno_dias_con_dato=len(horas),
            )
        )
    return RecuperacionRead(
        semanas=salida,
        bandas=bandas,
        sueno_objetivo_h=objetivo_sueno,
        conclusion=conclusiones.recuperacion(salida, objetivo_sueno),
    )


# ------------------------------------------------------ 4. ¿Voy hacia 11 %? --


async def composicion(
    session: AsyncSession, usuario_id: uuid.UUID, hoy: date, semanas: int
) -> ComposicionRead:
    primer_lunes = _lunes(hoy) - timedelta(weeks=semanas - 1)
    medidas = await repo.medidas_en_rango(session, usuario_id, primer_lunes, hoy)

    # Ultimo registro de cada semana (medidas ya vienen ordenadas por fecha).
    por_semana = {_lunes(m.fecha): m for m in medidas}
    filas = [
        SemanaComposicion(
            inicio=lunes,
            fecha_medida=m.fecha,
            peso_kg=float(m.peso_kg),
            cintura_cm=float(m.cintura_cm) if m.cintura_cm is not None else None,
        )
        for lunes, m in sorted(por_semana.items())
    ]

    cambio_peso = (
        redondear(filas[-1].peso_kg - filas[0].peso_kg, 2) if len(filas) >= 2 else None
    )
    con_cintura = [f for f in filas if f.cintura_cm is not None]
    cambio_cintura = (
        redondear((con_cintura[-1].cintura_cm or 0) - (con_cintura[0].cintura_cm or 0))
        if len(con_cintura) >= 2
        else None
    )
    usuario = await session.get(Usuario, usuario_id)
    objetivo = (
        float(usuario.peso_objetivo_kg)
        if usuario is not None and usuario.peso_objetivo_kg is not None
        else None
    )
    return ComposicionRead(
        semanas=filas,
        peso_objetivo_kg=objetivo,
        cambio_peso_kg=cambio_peso,
        cambio_cintura_cm=cambio_cintura,
        conclusion=conclusiones.composicion(
            filas, cambio_peso, cambio_cintura, objetivo
        ),
    )
