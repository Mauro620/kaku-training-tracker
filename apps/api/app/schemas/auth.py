"""Contratos de entrada y salida de los endpoints de autenticacion.

`SchemaBase` rechaza campos desconocidos (extra="forbid"): un typo del
cliente tiene que fallar con 422, no quedar como string vacio silencioso.
"""

from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.base import SchemaBase


class LoginRequest(SchemaBase):
    """Email + password. La unicidad del email esta en la DB; el formato
    lo valida Pydantic aca para devolver 422 con mensaje util en vez de
    un error de integridad."""

    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(SchemaBase):
    """El refresh token es opaco: el cliente lo manda tal cual lo recibio,
    sin transformarlo. El server lo hashea y busca por hash."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(SchemaBase):
    """Respuesta de login y refresh. `expires_in` es en segundos (900 = 15 min)
    para que el cliente pueda programar la renovacion sin parsear el JWT."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
