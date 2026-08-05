"""Dependencias de FastAPI compartidas por routers.

`get_usuario_actual` decodifica el JWT del header y devuelve el `Usuario`
asociado. Cualquier endpoint protegido la usa como Depends.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import decodificar_access_token
from app.db.session import get_session
from app.models import AuthUsuario, Usuario

# `auto_error=False` para no devolver 403 con el mensaje default de FastAPI
# cuando falta el header: queremos un 401 con nuestro mensaje.
_bearer = HTTPBearer(auto_error=False)


async def get_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    sesion: AsyncSession = Depends(get_session),
) -> Usuario:
    """Decodifica el JWT y devuelve el Usuario. 401 si el token falta,
    expiro o no matchea con ningun AuthUsuario."""
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token de autenticacion requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        usuario_id = decodificar_access_token(credenciales.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token invalido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    auth = await sesion.scalar(
        select(AuthUsuario).where(AuthUsuario.usuario_id == usuario_id)
    )
    if auth is None:
        # Token firmado valido pero el AuthUsuario fue borrado: tratar como
        # 401, no como 404. Un cliente con token "fantasma" no debe poder
        # inferir el estado de la cuenta.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token invalido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = await sesion.get(Usuario, auth.usuario_id)
    if usuario is None:
        # Idem: la FK a usuario deberia garantizar consistencia, pero si por
        # algo se rompe, no se filtra informacion al cliente.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token invalido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario
