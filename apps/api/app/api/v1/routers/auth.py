"""Endpoints de autenticacion.

Sin servicio ni repositorio: auth es framework-edge y no tiene logica de
negocio todavia. Cuando crezca, los routers de Fase 3+ van a usar service
y repo, y este queda como el unico router directo al modelo.
"""

from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_usuario_actual
from app.core.seguridad import (
    ACCESS_TOKEN_TTL_MINUTOS,
    crear_access_token,
    generar_refresh_token,
    hashear_refresh_token,
    refresh_expira_en,
    verificar_password,
)
from app.db.session import get_session
from app.models import AuthUsuario, Usuario
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Helpers ----------


async def _cargar_auth_por_email(
    sesion: AsyncSession, email: str
) -> AuthUsuario | None:
    # `scalar()` devuelve Any en async SQLAlchemy 2; el cast afirma el tipo
    # sin cambiar el valor en runtime.
    return cast(
        "AuthUsuario | None",
        await sesion.scalar(select(AuthUsuario).where(AuthUsuario.email == email)),
    )


# ---------- Endpoints ----------


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login con email y password. Devuelve access + refresh.",
)
async def login(
    payload: LoginRequest,
    sesion: AsyncSession = Depends(get_session),
) -> TokenResponse:
    auth = await _cargar_auth_por_email(sesion, payload.email)
    # Mensaje generico: no filtrar si el email existe o si la password esta mal.
    if auth is None or not verificar_password(payload.password, auth.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciales invalidas",
        )

    refresh = generar_refresh_token()
    auth.refresh_token_hash = hashear_refresh_token(refresh)
    auth.refresh_token_expira_en = refresh_expira_en()
    auth.ultimo_acceso_en = datetime.now(UTC)
    await sesion.commit()

    return TokenResponse(
        access_token=crear_access_token(auth.usuario_id),
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_TTL_MINUTOS * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rota el refresh y devuelve un access nuevo.",
)
async def refresh(
    payload: RefreshRequest,
    sesion: AsyncSession = Depends(get_session),
) -> TokenResponse:
    hash_recibido = hashear_refresh_token(payload.refresh_token)
    auth = cast(
        "AuthUsuario | None",
        await sesion.scalar(
            select(AuthUsuario).where(AuthUsuario.refresh_token_hash == hash_recibido)
        ),
    )
    ahora = datetime.now(UTC)
    if (
        auth is None
        or auth.refresh_token_expira_en is None
        or auth.refresh_token_expira_en < ahora
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh invalido o expirado",
        )

    nuevo_refresh = generar_refresh_token()
    auth.refresh_token_hash = hashear_refresh_token(nuevo_refresh)
    auth.refresh_token_expira_en = refresh_expira_en()
    await sesion.commit()

    return TokenResponse(
        access_token=crear_access_token(auth.usuario_id),
        refresh_token=nuevo_refresh,
        expires_in=ACCESS_TOKEN_TTL_MINUTOS * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalida el refresh rotandolo a NULL.",
)
async def logout(
    payload: RefreshRequest,
    sesion: AsyncSession = Depends(get_session),
) -> Response:
    hash_recibido = hashear_refresh_token(payload.refresh_token)
    auth = cast(
        "AuthUsuario | None",
        await sesion.scalar(
            select(AuthUsuario).where(AuthUsuario.refresh_token_hash == hash_recibido)
        ),
    )
    if auth is not None:
        # Idempotente: si el token no matchea, el "logout" ya esta hecho de
        # hecho. Devolver 204 igual para no filtrar estado de la cuenta.
        auth.refresh_token_hash = None
        auth.refresh_token_expira_en = None
        await sesion.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Endpoint protegido de prueba, para verificar end-to-end que el JWT cierra
# el circulo. Se saca en el siguiente commit cuando arranque Fase 3 con los
# endpoints de sueno, que ya dependen de get_usuario_actual.
@router.get(
    "/me",
    summary="Devuelve el usuario autenticado. Solo para smoke-test del token.",
)
async def me(usuario: Usuario = Depends(get_usuario_actual)) -> dict[str, str]:
    return {"id": str(usuario.id), "nombre": usuario.nombre}
