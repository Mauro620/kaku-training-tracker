"""Hashing, JWT y refresh tokens.

HS256 alcanza para Fase 3: emisor y verificador son el mismo proceso. Cuando
entre un segundo issuer se migra a RS256 tocando solo este modulo y el
setting `jwt_secret_key`.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

# ---------- Constantes ----------

ACCESS_TOKEN_TTL_MINUTOS = 15
REFRESH_TOKEN_TTL_DIAS = 30
ALGORITMO_JWT = "HS256"

# ---------- Passwords (argon2id) ----------

_hasher = PasswordHasher()


def hashear_password(plain: str) -> str:
    return _hasher.hash(plain)


def verificar_password(plain: str, hash: str) -> bool:
    try:
        return _hasher.verify(hash, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        # Hash corrupto o version incompatible: login falla, no explota.
        return False


# ---------- Refresh tokens (opacos, hasheados) ----------


def generar_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hashear_refresh_token(token: str) -> str:
    # SHA-256 alcanza: el input es de alta entropia (48 bytes random), no es
    # una contrasena humana. argon2 aca seria CPU al pedo.
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_expira_en() -> datetime:
    return datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_TTL_DIAS)


# ---------- Access tokens (JWT) ----------


def _claves() -> tuple[str, str]:
    clave = get_settings().jwt_secret_key
    if not clave:
        raise RuntimeError(
            "JWT_SECRET_KEY no configurado. "
            "Definilo en .env.local o como variable de entorno."
        )
    return clave, ALGORITMO_JWT


def crear_access_token(usuario_id: uuid.UUID) -> str:
    clave, algoritmo = _claves()
    ahora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "type": "access",
        "iat": ahora,
        "exp": ahora + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTOS),
    }
    return jwt.encode(payload, clave, algorithm=algoritmo)


def decodificar_access_token(token: str) -> uuid.UUID:
    """Lanza `jwt.PyJWTError` si el token es invalido, expiro o la firma no
    coincide. El router captura esa excepcion y responde 401."""
    clave, algoritmo = _claves()
    payload = jwt.decode(token, clave, algorithms=[algoritmo])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("el token no es de tipo access")
    return uuid.UUID(payload["sub"])
