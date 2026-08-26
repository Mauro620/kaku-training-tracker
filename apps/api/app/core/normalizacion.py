"""Normalizacion de texto. Dos funciones con intenciones distintas.

La division no es accidental: la busqueda del listado conserva
parentesis y porcentajes (el usuario escribe lo que ve en pantalla y
quiere encontrar exactamente eso), mientras que la deduplicacion del
importador los borra (un LLM que aclara "Pallof press (anti-rotacion)"
no deberia duplicar al "Pallof press" del catalogo).
"""

import re
import unicodedata

_PARENTESIS = re.compile(r"\([^)]*\)")
_PORCENTAJE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
_ESPACIOS = re.compile(r"\s+")


def _base(texto: str) -> str:
    """Pasos comunes: NFD + sin marcas + minusculas + colapsar espacios."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return _ESPACIOS.sub(" ", texto).strip()


def normalizar_para_busqueda(texto: str) -> str:
    """La del listado (`?q=`): conserva parentesis y porcentajes, solo
    normaliza acentos, mayusculas y espacios. Un usuario que busca
    "press (con banda)" debe encontrar "Press banca (con banda)"."""
    return _base(texto)


def normalizar_para_indice(texto: str) -> str:
    """La del importador: borra parentesis y porcentajes para que
    "Pallof press" y "Pallof press (anti-rotacion)" sean el mismo.

    El comportamiento es deliberado, no un descuido: aceptar el
    duplicado con sufijo entre parentesis es peor que colapsarlo (el
    catalogo se llena de basura con cada importacion)."""
    texto = _PARENTESIS.sub(" ", _base(texto))
    return _PORCENTAJE.sub(" ", texto).strip()
