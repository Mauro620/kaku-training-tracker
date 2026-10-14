"""Casos de REGLAS_NEGOCIO §17 tal cual, sin base de datos."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.metricas.calculo import (
    calcular_acwr,
    carga_planeada,
    clasificar_acwr,
    e1rm_epley,
    pct_ejecutado,
    porcentaje,
    promedio,
)


def test_pct_ejecutado_cuenta_movido_y_saca_descartado_del_denominador() -> None:
    # 6 planes: 3 cumplido, 1 movido, 1 descartado, 1 pendiente -> 4 / 5
    assert pct_ejecutado(cumplido=3, movido=1, descartado=1, planeadas=6) == 80.0


def test_pct_ejecutado_es_null_si_todo_se_descarto() -> None:
    assert pct_ejecutado(cumplido=0, movido=0, descartado=2, planeadas=2) is None


def test_pct_ejecutado_es_null_sin_planes() -> None:
    assert pct_ejecutado(cumplido=0, movido=0, descartado=0, planeadas=0) is None


def test_pct_ejecutado_es_cero_si_hay_planes_y_ninguno_se_hizo() -> None:
    assert pct_ejecutado(cumplido=0, movido=0, descartado=0, planeadas=4) == 0.0


def test_carga_planeada_suma_rpe_por_minutos() -> None:
    assert carga_planeada([(6, 60), (8, 90)]) == 1080


def test_carga_planeada_ignora_planes_incompletos() -> None:
    assert carga_planeada([(6, 60), (None, 90), (8, None), (None, None)]) == 360


def test_promedio_del_sueno_sobre_los_dias_con_registro() -> None:
    assert promedio([Decimal("7.0"), Decimal("8.0")]) == 7.5


def test_promedio_sin_datos_es_null_no_cero() -> None:
    assert promedio([]) is None


@pytest.mark.parametrize(
    ("parte", "total", "esperado"), [(5, 7, 71.4), (0, 7, 0.0), (7, 7, 100.0)]
)
def test_porcentaje_de_habitos(parte: int, total: int, esperado: float) -> None:
    assert porcentaje(parte, total) == esperado


def test_porcentaje_sin_denominador_es_null() -> None:
    assert porcentaje(0, 0) is None


# ------------------------------------------------- 1RM de Epley (§18.2) --

_DIV = Decimal("30")


@pytest.mark.parametrize(
    ("peso", "reps", "esperado"),
    [("100", 1, "100.0"), ("100", 5, "116.7"), ("80", 10, "106.7")],
)
def test_epley(peso: str, reps: int, esperado: str) -> None:
    rm = e1rm_epley(Decimal(peso), reps, divisor=_DIV)
    assert round(float(rm), 1) == float(esperado)


# --------------------------------------------- ACWR y semaforo (§3, §18.3) --

FIN = date(2026, 10, 12)
PRIMERA = date(2026, 6, 1)


def _carga(aguda: int, total_28d: int) -> dict[date, int]:
    """Aguda en el ultimo dia; el resto del total 28d en el primero de la ventana
    (fuera de los 7 dias agudos)."""
    return {FIN: aguda, FIN - timedelta(days=27): total_28d - aguda}


@pytest.mark.parametrize(
    ("aguda", "total", "acwr", "semaforo"),
    [
        (2000, 7400, 1.081, "verde"),
        (2400, 6000, 1.6, "rojo"),
        (1200, 6000, 0.8, "verde"),
        (1950, 6000, 1.3, "verde"),
        (2250, 6000, 1.5, "amarillo"),
        (1000, 6000, 0.667, "baja"),
    ],
)
def test_acwr_y_semaforo_con_los_casos_del_documento(
    aguda: int, total: int, acwr: float, semaforo: str
) -> None:
    valor = calcular_acwr(
        _carga(aguda, total), FIN, PRIMERA, dias_agudo=7, dias_cronico=28
    )
    assert valor == acwr
    assert (
        clasificar_acwr(valor, min_seguro=0.8, max_seguro=1.3, alerta=1.5) == semaforo
    )


def test_acwr_es_null_con_carga_cronica_cero() -> None:
    assert calcular_acwr({}, FIN, PRIMERA, dias_agudo=7, dias_cronico=28) is None


def test_acwr_es_null_con_menos_de_28_dias_de_historia() -> None:
    primera = FIN - timedelta(days=19)  # 20 dias de historia
    assert (
        calcular_acwr(_carga(2000, 7400), FIN, primera, dias_agudo=7, dias_cronico=28)
        is None
    )
    # Con exactamente 28 dias ya se calcula.
    justo = FIN - timedelta(days=27)
    assert (
        calcular_acwr(_carga(2000, 7400), FIN, justo, dias_agudo=7, dias_cronico=28)
        == 1.081
    )


def test_acwr_es_null_sin_ninguna_sesion_registrada() -> None:
    assert calcular_acwr({}, FIN, None, dias_agudo=7, dias_cronico=28) is None


def test_semaforo_sin_dato() -> None:
    assert clasificar_acwr(None, min_seguro=0.8, max_seguro=1.3, alerta=1.5) is None


def test_los_ceros_cuentan_volver_de_un_paron_da_acwr_alto() -> None:
    # 3 semanas sin entrenar y una semana de 2000: cronica 500, aguda 2000.
    carga = {FIN - timedelta(days=k): 400 for k in range(5)}  # 5 sesiones, 2000
    valor = calcular_acwr(carga, FIN, PRIMERA, dias_agudo=7, dias_cronico=28)
    assert valor == 4.0
    assert clasificar_acwr(valor, min_seguro=0.8, max_seguro=1.3, alerta=1.5) == "rojo"
