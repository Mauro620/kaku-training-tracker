"""Base de los schemas de Pydantic.

Nunca se expone un modelo de SQLAlchemy directamente: los schemas separados por
intención (`Create`, `Update`, `Read`) son el contrato con el frontend, y el
OpenAPI que sale de ellos es lo que genera los tipos de TypeScript.
"""

from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    """Schema de entrada. Rechaza campos desconocidos: un typo en el cliente
    tiene que fallar fuerte, no perderse en silencio."""

    model_config = ConfigDict(extra="forbid")


class ReadBase(BaseModel):
    """Schema de salida. Lee directo del modelo de SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)
