"""Modelos de SQLAlchemy.

Importar este paquete registra TODAS las tablas en `Base.metadata`:
`alembic/env.py` depende de eso para que autogenerate vea el esquema completo.
Un modelo que no se re-exporte acá no existe para las migraciones.
"""

from app.db.base import Base
from app.models.bienestar import (
    Habito,
    HabitoRegistro,
    MedidaCorporal,
    Molestia,
    RegistroBienestar,
    RegistroHidratacion,
    RegistroSueno,
)
from app.models.catalogo import (
    AuthUsuario,
    Ejercicio,
    Parametro,
    TipoSesion,
    TipoTest,
    Usuario,
    ZonaCorporal,
)
from app.models.entrenamiento import (
    Ciclo,
    CicloSemana,
    Partido,
    Serie,
    SeriePlan,
    Sesion,
    SesionPlan,
)
from app.models.evaluacion import TestFisico, TestIntento
from app.models.nutricion import (
    Alimento,
    ComidaItem,
    ComidaLog,
    Despensa,
    Receta,
    RecetaItem,
)

__all__ = [
    "Alimento",
    "AuthUsuario",
    "Base",
    "Ciclo",
    "CicloSemana",
    "ComidaItem",
    "ComidaLog",
    "Despensa",
    "Ejercicio",
    "Habito",
    "HabitoRegistro",
    "MedidaCorporal",
    "Molestia",
    "Parametro",
    "Partido",
    "Receta",
    "RecetaItem",
    "RegistroBienestar",
    "RegistroHidratacion",
    "RegistroSueno",
    "Serie",
    "SeriePlan",
    "Sesion",
    "SesionPlan",
    "TestFisico",
    "TestIntento",
    "TipoSesion",
    "TipoTest",
    "Usuario",
    "ZonaCorporal",
]
