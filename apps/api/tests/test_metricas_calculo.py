"""Casos de REGLAS_NEGOCIO §17 tal cual, sin base de datos."""

from decimal import Decimal

import pytest

from app.services.metricas.calculo import (
    carga_planeada,
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
