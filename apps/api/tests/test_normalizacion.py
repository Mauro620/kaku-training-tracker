"""Tests de las funciones de normalizacion y de similitud.

Son funciones puras: viven en `app.core` y no tocan la base. La
normalizacion tiene dos formas deliberadamente separadas:

- `normalizar_para_busqueda`: la del listado filtrado por `?q=`. Conserva
  el texto casi como esta escrito, solo lo vuelve comparable (acentos,
  mayusculas, espacios).
- `normalizar_para_indice`: la del importador de planes. Borra
  parentesis y porcentajes para que un LLM que escribe
  "Pallof press (anti-rotacion)" matchee contra el "Pallof press" del
  catalogo.

El test de similitud cubre el caso de uso de la deteccion de duplicados
del feature 2.
"""


def test_busqueda_preserva_parentesis() -> None:
    from app.core.normalizacion import normalizar_para_busqueda

    assert normalizar_para_busqueda("Regate (con conos)") == "regate (con conos)"


def test_busqueda_preserva_porcentaje() -> None:
    from app.core.normalizacion import normalizar_para_busqueda

    assert "80%" in normalizar_para_busqueda("Fuerza al 80%")


def test_indice_colapsa_parentesis() -> None:
    from app.core.normalizacion import normalizar_para_indice

    assert normalizar_para_indice("Regate (con conos)") == "regate"


def test_indice_colapsa_porcentaje() -> None:
    from app.core.normalizacion import normalizar_para_indice

    assert normalizar_para_indice("Fuerza al 80%") == "fuerza al"


def test_normalizacion_quita_tildes() -> None:
    from app.core.normalizacion import (
        normalizar_para_busqueda,
        normalizar_para_indice,
    )

    assert normalizar_para_busqueda("Elevación") == "elevacion"
    assert normalizar_para_indice("Elevación") == "elevacion"


def test_normalizacion_minusculas() -> None:
    from app.core.normalizacion import (
        normalizar_para_busqueda,
        normalizar_para_indice,
    )

    assert normalizar_para_busqueda("HIP THRUST") == "hip thrust"
    assert normalizar_para_indice("HIP THRUST") == "hip thrust"


def test_normalizacion_espacios_multiples() -> None:
    from app.core.normalizacion import normalizar_para_busqueda

    assert normalizar_para_busqueda("a   b") == "a b"


def test_normalizacion_vacio() -> None:
    from app.core.normalizacion import (
        normalizar_para_busqueda,
        normalizar_para_indice,
    )

    assert normalizar_para_busqueda("") == ""
    assert normalizar_para_indice("") == ""


# ----------------------------------------------- similitud ------------------


def test_similitud_pallof_press_con_y_sin_parentesis() -> None:
    """El caso de uso del SPEC §4.1: una variacion con descripcion entre
    parentesis es candidata a duplicado, y el listado de posibles
    duplicados la tiene que traer."""
    from app.services.catalogo.similitud_service import similitud_entre_nombres

    assert (
        similitud_entre_nombres("Pallof press (anti-rotacion)", "Pallof press") >= 0.75
    )


def test_similitud_ignora_tildes_entre_elevacion_de_talon() -> None:
    from app.services.catalogo.similitud_service import similitud_entre_nombres

    assert similitud_entre_nombres("Elevacion de talon", "Elevación de talón") >= 0.9
