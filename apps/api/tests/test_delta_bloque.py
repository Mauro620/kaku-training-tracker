"""Tests del calculo de delta plan vs real (SPEC §2.1).

Funciones puras: reciben dataclasses locales (`BloqueDeltaInput`,
`BloquePlanDeltaInput`, `SesionDeltaInput`, `SesionPlanDeltaInput`),
no tocan SQLAlchemy ni la base. Asi son faciles de triangular y
rapidas de correr (no necesitan sesion ni Postgres).
"""

from app.services.catalogo.delta import (
    BloqueDeltaInput,
    BloquePlanDeltaInput,
    SesionDeltaInput,
    SesionPlanDeltaInput,
    delta_bloque,
    delta_sesion,
)

# -------------------------------------------------- delta de bloque ---------


def test_delta_bloque_carga() -> None:
    """Caso del SPEC: 3x8@80 contra objetivo 3x8@90 -> delta peso -10.
    Series y reps coinciden con el objetivo: delta 0."""
    real = BloqueDeltaInput(series=3, reps=8, peso_kg=80)
    plan = BloquePlanDeltaInput(series=3, reps_min=8, reps_max=8, peso_objetivo_kg=90)

    d = delta_bloque(real, plan)

    assert d.series == 0
    assert d.reps == 0
    assert d.peso_kg == -10
    assert d.distancia_m is None
    assert d.duracion_s is None


def test_delta_reps_dentro_de_rango() -> None:
    """7 reps contra rango 6-8 -> dentro del rango, delta 0."""
    real = BloqueDeltaInput(series=3, reps=7, peso_kg=80)
    plan = BloquePlanDeltaInput(series=3, reps_min=6, reps_max=8, peso_objetivo_kg=80)

    d = delta_bloque(real, plan)

    assert d.reps == 0


def test_delta_reps_sobre_rango() -> None:
    """10 reps contra rango 6-8 -> por encima del maximo, delta +2
    (10 - 8)."""
    real = BloqueDeltaInput(series=3, reps=10, peso_kg=80)
    plan = BloquePlanDeltaInput(series=3, reps_min=6, reps_max=8, peso_objetivo_kg=80)

    d = delta_bloque(real, plan)

    assert d.reps == 2


def test_delta_reps_bajo_rango() -> None:
    """5 reps contra rango 6-8 -> por debajo del minimo, delta -1
    (5 - 6)."""
    real = BloqueDeltaInput(series=3, reps=5, peso_kg=80)
    plan = BloquePlanDeltaInput(series=3, reps_min=6, reps_max=8, peso_objetivo_kg=80)

    d = delta_bloque(real, plan)

    assert d.reps == -1


def test_delta_objetivo_nulo() -> None:
    """Plan sin campos objetivo (rep min/max ni peso): todos los deltas
    de esos campos son NULL, no 0. NUNCA se asume cero. `series` SI
    tiene objetivo en este test, asi que su delta es 0."""
    real = BloqueDeltaInput(series=3, reps=8, peso_kg=80)
    plan = BloquePlanDeltaInput(
        series=3, reps_min=None, reps_max=None, peso_objetivo_kg=None
    )

    d = delta_bloque(real, plan)

    # series tiene objetivo: delta 0 (no es lo que el SPEC llama "nulo").
    assert d.series == 0
    # reps y peso NO tienen objetivo: delta NULL.
    assert d.reps is None
    assert d.peso_kg is None
    assert d.distancia_m is None
    assert d.duracion_s is None


def test_bloque_sin_plan() -> None:
    """`bloque_plan` ausente: todos los deltas son NULL. El bloque
    existe pero no tiene contra que compararse."""
    real = BloqueDeltaInput(series=3, reps=8, peso_kg=80)

    d = delta_bloque(real, None)

    assert d.series is None
    assert d.reps is None
    assert d.peso_kg is None
    assert d.distancia_m is None
    assert d.duracion_s is None


# ----------------------------------------------- delta de sesion ------------


def test_delta_sesion_sin_plan() -> None:
    """Sesion libre (sin `sesion_plan_id`): la funcion devuelve None y el
    caller sabe no intentar computar nada mas."""
    real = SesionDeltaInput(duracion_min=60, rpe=7, carga_srpe=420)

    assert delta_sesion(real, None) is None


def test_delta_sesion_duracion() -> None:
    """55 min reales contra 50 min estimados -> delta +5."""
    real = SesionDeltaInput(duracion_min=55, rpe=7, carga_srpe=385)
    plan = SesionPlanDeltaInput(duracion_min_est=50, rpe_objetivo=7)

    d = delta_sesion(real, plan)

    assert d is not None
    assert d.duracion_min == 5


def test_delta_sesion_duracion_sin_estimacion() -> None:
    """Plan sin `duracion_min_est` -> el delta puntual no se puede calcular,
    pero los demas si."""
    real = SesionDeltaInput(duracion_min=55, rpe=7, carga_srpe=385)
    plan = SesionPlanDeltaInput(duracion_min_est=None, rpe_objetivo=7)

    d = delta_sesion(real, plan)

    assert d is not None
    assert d.duracion_min is None
    assert d.rpe == 0
    assert d.carga_srpe is None  # porque depende de duracion_min_est


def test_delta_sesion_rpe() -> None:
    """9 real contra objetivo 7 -> delta +2."""
    real = SesionDeltaInput(duracion_min=55, rpe=9, carga_srpe=495)
    plan = SesionPlanDeltaInput(duracion_min_est=55, rpe_objetivo=7)

    d = delta_sesion(real, plan)

    assert d is not None
    assert d.rpe == 2


def test_delta_sesion_carga() -> None:
    """carga_srpe real 495 contra objetivo 55*7=385 -> delta +110.
    El delta de carga es el UNICO que se calcula contra la multiplicacion
    de los dos parametros del plan, no contra un campo directo."""
    real = SesionDeltaInput(duracion_min=55, rpe=9, carga_srpe=495)
    plan = SesionPlanDeltaInput(duracion_min_est=55, rpe_objetivo=7)

    d = delta_sesion(real, plan)

    assert d is not None
    assert d.carga_srpe == 110


def test_delta_sesion_carga_si_falta_algun_factor() -> None:
    """Falta `duracion_min_est` o `rpe_objetivo` -> no se puede estimar la
    carga objetivo, delta NULL."""
    real = SesionDeltaInput(duracion_min=55, rpe=9, carga_srpe=495)
    plan = SesionPlanDeltaInput(duracion_min_est=55, rpe_objetivo=None)

    d = delta_sesion(real, plan)

    assert d is not None
    assert d.carga_srpe is None
