"""Routers de la API v1.

Cada modulo expone un `router` (FastAPI APIRouter). main.py los monta
contra el APIRouter raiz del prefijo /api/v1.

El __init__ reexporta cada router con un nombre estable para que main.py
no tenga que cambiar cuando se agrega un router nuevo: solo anadir la
linea de import aca.
"""

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.bienestar import router as bienestar_router
from app.api.v1.routers.catalogos import router as catalogos_router
from app.api.v1.routers.entrenamiento import router as entrenamiento_router
from app.api.v1.routers.habitos import router as habitos_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.hidratacion import router as hidratacion_router
from app.api.v1.routers.molestias import router as molestias_router
from app.api.v1.routers.parametros import router as parametros_router
from app.api.v1.routers.sueno import router as sueno_router

__all__ = [
    "auth_router",
    "bienestar_router",
    "catalogos_router",
    "entrenamiento_router",
    "habitos_router",
    "health_router",
    "hidratacion_router",
    "molestias_router",
    "parametros_router",
    "sueno_router",
]
