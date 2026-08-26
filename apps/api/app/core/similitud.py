"""Similitud difusa para detectar duplicados de ejercicios.

Pivote (PR 1 del feature 2): se arranco con `difflib.SequenceMatcher`
porque era stdlib y alcanza para el universo chico, pero el caso del
SPEC "Pallof press (anti-rotacion)" vs "Pallof press" daba 0.60 — por
debajo del umbral 0.75 que necesita el listado de posibles duplicados.
El cambio a `rapidfuzz.fuzz.token_set_ratio` es local al cuerpo de la
funcion: la firma y el contrato [0, 1] se mantienen, y el resto del
proyecto (services, routers, tests) no se entera.

`token_set_ratio` mide interseccion de tokens sin importar orden ni
repetidos, que es exactamente lo que queremos cuando un sufijo entre
parentesis se agrega o se quita.
"""

from rapidfuzz import fuzz

from app.core.normalizacion import normalizar_para_busqueda


def _similitud_normalizada(a: str, b: str) -> float:
    """Ratio de similitud en [0, 1]. Cuanto mas cerca de 1, mas probable
    que los dos nombres se refieran al mismo ejercicio."""
    return (
        fuzz.token_set_ratio(normalizar_para_busqueda(a), normalizar_para_busqueda(b))
        / 100.0
    )
