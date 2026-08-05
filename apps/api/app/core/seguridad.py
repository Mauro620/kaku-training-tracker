"""Hashing, JWT y refresh tokens.

HS256 alcanza para Fase 3: emisor y verificador son el mismo proceso. Cuando
entre un segundo issuer se migra a RS256 tocando solo este modulo y el
setting `jwt_secret_key`. El algoritmo y los TTL salen de `Settings`, nunca
como literal: son exactamente el tipo de umbral que AGENTS.md prohibe
hardcodear.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

# ---------- Passwords (argon2id) ----------

_hasher = PasswordHasher()

# Hash valido de una contrasena que nadie va a adivinar. Se usa como senuelo
# cuando el email no existe, para que argon2 corra igual y el tiempo de
# respuesta no filtre si la cuenta existe (timing oracle).
_HASH_SENUELO = _hasher.hash(secrets.token_urlsafe(32))


def hashear_password(plain: str) -> str:
    return _hasher.hash(plain)


def verificar_password(plain: str, hash: str | None) -> bool:
    """`hash=None` verifica igual contra un senuelo: mantiene el costo de
    CPU constante entre "email no existe" y "email existe, password mala",
    para que el tiempo de respuesta no distinga los dos casos."""
    try:
        return _hasher.verify(hash or _HASH_SENUELO, plain) and hash is not None
    except VerifyMismatchError:
        return False
    except InvalidHashError:
        # Hash corrupto o de una version de argon2 incompatible: el login
        # falla, no explota con un 500.
        return False


# ---------- Refresh tokens (opacos, hasheados) ----------


def generar_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hashear_refresh_token(token: str) -> str:
    # SHA-256 alcanza: el input es de alta entropia (48 bytes random), no es
    # una contrasena humana. argon2 aca seria CPU al pedo.
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_expira_en() -> datetime:
    return datetime.now(UTC) + timedelta(days=get_settings().refresh_token_expire_days)


# ---------- Access tokens (JWT) ----------


def _claves() -> tuple[str, str]:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY no configurado. "
            "Definilo en .env.local o como variable de entorno."
        )
    return settings.jwt_secret_key, settings.jwt_algorithm


def crear_access_token(usuario_id: uuid.UUID) -> str:
    clave, algoritmo = _claves()
    ahora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "type": "access",
        "iat": ahora,
        "exp": ahora + timedelta(minutes=get_settings().access_token_expire_minutes),
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
