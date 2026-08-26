"""Excepciones de dominio.

Los servicios levantan estas, nunca `HTTPException` (AGENTS.md §5). El
manejador central en `main.py` las traduce a HTTP.
"""


class DomainError(Exception):
    """Base de las excepciones de dominio."""


class InvarianteDeNegocioError(DomainError):
    """Un dato es individualmente válido pero viola una regla que cruza
    varios campos (ej. la fecha de un registro de sueño no coincide con la
    fecha local de `fin`). Se traduce a 422: el request está bien formado
    pero es semánticamente inconsistente."""


class RecursoNoEncontradoError(DomainError):
    """El recurso no existe, o no pertenece al usuario autenticado. Se
    traduce a 404 sin distinguir los dos casos: no hay más de un usuario
    hoy, pero la distinción no debe filtrarse igual."""


class ConflictoDeNegocioError(InvarianteDeNegocioError):
    """409. La operacion es valida contra el esquema pero choca con el
    estado actual: un nombre ya tomado, una fusion que rompe la historia,
    un borrado de algo con referencias. Distinta de 422: ahi el problema
    esta en lo que manda el cliente; aci el problema esta contra el
    estado del servidor. Sigue siendo `InvarianteDeNegocioError` para que
    un `except InvarianteDeNegocioError` siga siendo util: el caller que
    no distinga 422 de 409 tiene una sola clausula y el handler central
    traduce segun la clase concreta."""
