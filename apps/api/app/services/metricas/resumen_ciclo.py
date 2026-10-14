"""Resumen de ciclo para el LLM (REGLAS_NEGOCIO §17).

Lee el ciclo actual (o el ultimo cerrado) y lo agrega por semana. No escribe ni
define metricas nuevas: reutiliza sRPE (§1), rango de semana (§13.1) y el
progreso de tests (§7, §8).
"""

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import (
    Ciclo,
    CicloSemana,
    HabitoRegistro,
    MedidaCorporal,
    Sesion,
    SesionPlan,
    TestFisico,
    TipoTest,
)
from app.models.enums import EstadoSesionPlan
from app.repositories import entrenamiento as repo_entrenamiento
from app.repositories import metricas as repo
from app.schemas.metricas.resumen_ciclo import (
    CambioCorporal,
    CargaSemana,
    CicloResumen,
    CumplimientoSemana,
    HabitoSemana,
    MedidaResumen,
    PlaneadoVsReal,
    PromedioDiario,
    PruebaResumen,
    ResultadoPrueba,
    ResumenCicloRead,
    SemanaResumen,
    SesionResumen,
    TotalesCiclo,
)
from app.services.catalogo import parametro as parametros
from app.services.entrenamiento.ciclo import calcular_rango_semana
from app.services.evaluacion.calculo import (
    calcular_pct_cambio,
    calcular_pct_decremento,
    mejor_intento,
)
from app.services.evaluacion.test_fisico import CODIGO_RSA
from app.services.metricas.calculo import (
    carga_planeada,
    pct_ejecutado,
    porcentaje,
    promedio,
    redondear,
)

_CLAVE_OBJETIVO_SUENO = "sueno_objetivo_horas"
_CLAVE_OBJETIVO_AGUA = "hidratacion_objetivo_ml"


async def construir_resumen_ciclo(
    session: AsyncSession, usuario_id: uuid.UUID, hoy: date
) -> ResumenCicloRead:
    ciclo = await repo.ciclo_resumible(session, usuario_id)
    if ciclo is None:
        raise RecursoNoEncontradoError(
            "no hay un ciclo activo ni cerrado del que armar el resumen"
        )

    fin_efectivo = ciclo.fecha_cierre_real or ciclo.fecha_fin_prevista
    corte = min(hoy, fin_efectivo)

    semanas = await repo_entrenamiento.listar_ciclo_semanas_por_ciclo(session, ciclo.id)
    planes = await repo.planes_del_ciclo(session, ciclo.id)
    sesiones = await repo.sesiones_en_rango(
        session, usuario_id, ciclo.fecha_inicio, corte
    )
    sueno = await repo.sueno_en_rango(session, usuario_id, ciclo.fecha_inicio, corte)
    agua = await repo.hidratacion_en_rango(
        session, usuario_id, ciclo.fecha_inicio, corte
    )
    habitos = await repo.habitos_activos(session, usuario_id)
    registros = await repo.registros_de_habitos_en_rango(
        session, [h.id for h in habitos], ciclo.fecha_inicio, corte
    )
    medidas = await repo.medidas_en_rango(
        session, usuario_id, ciclo.fecha_inicio, corte
    )

    objetivo_sueno = float(
        (await parametros.obtener(session, _CLAVE_OBJETIVO_SUENO)).valor
    )
    objetivo_agua = float(
        (await parametros.obtener(session, _CLAVE_OBJETIVO_AGUA)).valor
    )

    semanas_out: list[SemanaResumen] = []
    for semana in semanas:
        inicio, fin = calcular_rango_semana(ciclo.fecha_inicio, semana.numero)
        if inicio > corte:
            continue
        ultimo = min(fin, corte)
        planes_semana = [(p, t) for p, t, n in planes if n == semana.numero]
        semanas_out.append(
            _armar_semana(
                semana,
                inicio=inicio,
                fin=fin,
                ultimo=ultimo,
                completa=fin <= corte,
                planes=planes_semana,
                sesiones=[(s, t) for s, t in sesiones if inicio <= s.fecha <= fin],
                sueno=[h for f, h in sueno if inicio <= f <= ultimo],
                agua=[ml for f, ml in agua if inicio <= f <= ultimo],
                habitos=[
                    (h.nombre, [r for r in registros if r.habito_id == h.id])
                    for h in habitos
                ],
                medidas=[m for m in medidas if inicio <= m.fecha <= fin],
                objetivo_sueno=objetivo_sueno,
                objetivo_agua=objetivo_agua,
            )
        )

    return ResumenCicloRead(
        ciclo=CicloResumen(
            numero=ciclo.numero,
            objetivo=ciclo.objetivo,
            estado=ciclo.estado.value,
            fecha_inicio=ciclo.fecha_inicio,
            fecha_fin_prevista=ciclo.fecha_fin_prevista,
            fecha_cierre_real=ciclo.fecha_cierre_real,
            semanas_totales=ciclo.semanas,
            informado_hasta=corte,
        ),
        totales=_totales(semanas_out),
        semanas=semanas_out,
        pruebas=await _pruebas(session, usuario_id, ciclo, corte),
        cambio_corporal=_cambio_corporal(medidas),
    )


def _cumplimiento(
    planes: list[tuple[SesionPlan, str]], sin_plan: int
) -> CumplimientoSemana:
    por_estado = dict.fromkeys(EstadoSesionPlan, 0)
    for plan, _tipo in planes:
        por_estado[plan.estado] += 1
    return CumplimientoSemana(
        planeadas=len(planes),
        cumplido=por_estado[EstadoSesionPlan.cumplido],
        movido=por_estado[EstadoSesionPlan.movido],
        descartado=por_estado[EstadoSesionPlan.descartado],
        pendiente=por_estado[EstadoSesionPlan.pendiente],
        sesiones_sin_plan=sin_plan,
        pct_ejecutado=pct_ejecutado(
            cumplido=por_estado[EstadoSesionPlan.cumplido],
            movido=por_estado[EstadoSesionPlan.movido],
            descartado=por_estado[EstadoSesionPlan.descartado],
            planeadas=len(planes),
        ),
    )


def _armar_semana(
    semana: CicloSemana,
    *,
    inicio: date,
    fin: date,
    ultimo: date,
    completa: bool,
    planes: list[tuple[SesionPlan, str]],
    sesiones: list[tuple[Sesion, str]],
    sueno: list[Decimal],
    agua: list[int],
    habitos: list[tuple[str, list[HabitoRegistro]]],
    medidas: list[MedidaCorporal],
    objetivo_sueno: float,
    objetivo_agua: float,
) -> SemanaResumen:
    real_por_plan = {s.sesion_plan_id: s for s, _ in sesiones if s.sesion_plan_id}
    # Libre = sin plan. Una sesion ligada a un plan de otra semana no es libre:
    # cuenta en la carga real pero no como "sin plan".
    libres = [(s, t) for s, t in sesiones if s.sesion_plan_id is None]

    filas: list[SesionResumen] = []
    pares: list[tuple[SesionPlan, Sesion]] = []
    for plan, tipo in planes:
        real = real_por_plan.get(plan.id)
        if real is not None:
            pares.append((plan, real))
        filas.append(
            SesionResumen(
                dia_sugerido=plan.dia_sugerido,
                fecha_real=real.fecha if real else None,
                tipo=tipo,
                nombre=plan.nombre,
                estado_plan=plan.estado.value,
                rpe_planeado=plan.rpe_objetivo,
                rpe_real=real.rpe if real else None,
                duracion_planeada_min=plan.duracion_min_est,
                duracion_real_min=real.duracion_min if real else None,
                carga_srpe=real.carga_srpe if real else None,
            )
        )
    for real, tipo in libres:
        filas.append(
            SesionResumen(
                dia_sugerido=None,
                fecha_real=real.fecha,
                tipo=tipo,
                nombre=None,
                estado_plan=None,
                rpe_planeado=None,
                rpe_real=real.rpe,
                duracion_planeada_min=None,
                duracion_real_min=real.duracion_min,
                carga_srpe=real.carga_srpe,
            )
        )

    transcurridos = (ultimo - inicio).days + 1
    pares_rpe = [(p, r) for p, r in pares if p.rpe_objetivo is not None]
    return SemanaResumen(
        numero=semana.numero,
        fase=semana.fase.value,
        volumen_pct=semana.volumen_pct,
        rpe_objetivo_min=semana.rpe_objetivo_min,
        rpe_objetivo_max=semana.rpe_objetivo_max,
        inicio=inicio,
        fin=fin,
        estado="completa" if completa else "en_curso",
        cumplimiento=_cumplimiento(planes, len(libres)),
        planeado_vs_real=PlaneadoVsReal(
            pares=len(pares),
            rpe_planeado_prom=promedio(
                p.rpe_objetivo for p, _ in pares_rpe if p.rpe_objetivo
            ),
            rpe_real_prom=promedio(r.rpe for _, r in pares_rpe),
            duracion_planeada_min=sum(
                p.duracion_min_est for p, _ in pares if p.duracion_min_est
            ),
            duracion_real_min=sum(
                r.duracion_min for p, r in pares if p.duracion_min_est
            ),
        ),
        carga=CargaSemana(
            planeada=carga_planeada(
                [(p.rpe_objetivo, p.duracion_min_est) for p, _ in planes]
            ),
            real=sum(s.carga_srpe for s, _ in sesiones),
        ),
        sesiones=filas,
        sueno_horas=PromedioDiario(
            promedio=promedio(sueno), dias_con_dato=len(sueno), objetivo=objetivo_sueno
        ),
        agua_ml=PromedioDiario(
            promedio=promedio(agua), dias_con_dato=len(agua), objetivo=objetivo_agua
        ),
        habitos=[
            _habito_semana(nombre, registros_h, inicio, ultimo, transcurridos)
            for nombre, registros_h in habitos
        ],
        medidas=[
            MedidaResumen(
                fecha=m.fecha,
                peso_kg=float(m.peso_kg),
                cintura_cm=float(m.cintura_cm) if m.cintura_cm is not None else None,
            )
            for m in medidas
        ],
    )


def _habito_semana(
    nombre: str,
    registros: list[HabitoRegistro],
    inicio: date,
    ultimo: date,
    transcurridos: int,
) -> HabitoSemana:
    en_semana = [r for r in registros if inicio <= r.fecha <= ultimo]
    cumplidos = sum(1 for r in en_semana if r.valor)
    return HabitoSemana(
        nombre=nombre,
        dias_cumplidos=cumplidos,
        dias_con_registro=len(en_semana),
        dias_transcurridos=transcurridos,
        pct_cumplimiento=porcentaje(cumplidos, transcurridos),
    )


def _totales(semanas: list[SemanaResumen]) -> TotalesCiclo:
    def suma(campo: str) -> int:
        return sum(getattr(s.cumplimiento, campo) for s in semanas)

    cumplido, movido, descartado = suma("cumplido"), suma("movido"), suma("descartado")
    return TotalesCiclo(
        cumplimiento=CumplimientoSemana(
            planeadas=suma("planeadas"),
            cumplido=cumplido,
            movido=movido,
            descartado=descartado,
            pendiente=suma("pendiente"),
            sesiones_sin_plan=suma("sesiones_sin_plan"),
            pct_ejecutado=pct_ejecutado(
                cumplido=cumplido,
                movido=movido,
                descartado=descartado,
                planeadas=suma("planeadas"),
            ),
        ),
        carga_real=sum(s.carga.real for s in semanas),
        carga_planeada=sum(s.carga.planeada for s in semanas),
    )


async def _pruebas(
    session: AsyncSession, usuario_id: uuid.UUID, ciclo: Ciclo, corte: date
) -> list[PruebaResumen]:
    historico = await repo.tests_con_tipo_hasta(session, usuario_id, corte)
    por_tipo: dict[int, list[tuple[TestFisico, TipoTest]]] = defaultdict(list)
    for test, tipo in historico:
        por_tipo[tipo.id].append((test, tipo))

    salida: list[PruebaResumen] = []
    for filas in por_tipo.values():
        tipo = filas[0][1]
        base_test = filas[0][0]  # el primero del historico (§8)
        base = mejor_intento([i.valor for i in base_test.intentos], tipo.mejor_es_mayor)
        resultados: list[ResultadoPrueba] = []
        for test, _ in filas:
            if test.fecha < ciclo.fecha_inicio:
                continue
            valores = [i.valor for i in test.intentos]
            mejor = mejor_intento(valores, tipo.mejor_es_mayor)
            resultados.append(
                ResultadoPrueba(
                    fecha=test.fecha,
                    mejor=float(mejor),
                    media=redondear(sum(valores, Decimal("0")) / len(valores), 3),
                    pct_decremento=(
                        float(d)
                        if tipo.codigo == CODIGO_RSA
                        and (d := calcular_pct_decremento(valores)) is not None
                        else None
                    ),
                    pct_cambio_vs_base=(
                        None
                        if test.id == base_test.id
                        else float(
                            calcular_pct_cambio(base, mejor, tipo.mejor_es_mayor)
                        )
                    ),
                )
            )
        if resultados:
            salida.append(
                PruebaResumen(
                    codigo=tipo.codigo,
                    nombre=tipo.nombre,
                    unidad=tipo.unidad,
                    mejor_es_mayor=tipo.mejor_es_mayor,
                    base_fecha=base_test.fecha,
                    base_mejor=float(base),
                    resultados=resultados,
                )
            )
    return salida


def _cambio_corporal(medidas: list[MedidaCorporal]) -> CambioCorporal | None:
    if not medidas:
        return None
    primera, ultima = medidas[0], medidas[-1]
    con_cintura = [m for m in medidas if m.cintura_cm is not None]
    cintura = None
    if len(con_cintura) >= 2 and con_cintura[0].cintura_cm is not None:
        ultima_cintura = con_cintura[-1].cintura_cm
        assert ultima_cintura is not None
        cintura = redondear(ultima_cintura - con_cintura[0].cintura_cm)
    return CambioCorporal(
        peso_inicial_kg=float(primera.peso_kg),
        peso_final_kg=float(ultima.peso_kg),
        cambio_peso_kg=redondear(ultima.peso_kg - primera.peso_kg, 2),
        cambio_cintura_cm=cintura,
    )
