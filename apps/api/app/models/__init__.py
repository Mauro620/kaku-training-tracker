"""Modelos de SQLAlchemy.

Importar este paquete tiene que registrar TODAS las tablas en `Base.metadata`:
`alembic/env.py` depende de eso para que autogenerate vea el esquema completo.
Cada modelo nuevo se re-exporta acá.
"""

from app.db.base import Base

__all__ = ["Base"]
