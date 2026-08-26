"""Wrapper publico para la similitud. Existe como service para que el
router no importe de `app.core` (mantiene el patron de ARCHITECTURE §2:
los services son la frontera que consume el router)."""

from app.core.similitud import _similitud_normalizada


def similitud_entre_nombres(a: str, b: str) -> float:
    """Similitud entre dos nombres de ejercicio, en [0, 1]."""
    return _similitud_normalizada(a, b)
