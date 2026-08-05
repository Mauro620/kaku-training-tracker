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
