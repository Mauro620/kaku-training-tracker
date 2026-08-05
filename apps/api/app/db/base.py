"""Base declarativa y convención de nombres de restricciones.

La `naming_convention` no es cosmética: sin ella Postgres bautiza las
restricciones y los índices con nombres que Alembic no puede predecir, y el
día que haya que hacer un `drop_constraint` en una migración no hay nombre al
cual referirse. Se define una vez, acá, antes del primer modelo.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
