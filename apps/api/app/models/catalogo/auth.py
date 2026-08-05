"""Identidad de login separada del dominio.

Tabla 1:1 con `usuario` por PK = FK. Asi `usuario` no se llena de columnas de
auth (email, password, refresh) que pertenecen a otro bounded context.

El refresh_token_hash se rota a NULL en logout. NULL equivale a "sin sesion
activa" y sirve para invalidar sesiones sin esperar a que expire el TTL.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthUsuario(Base):
    __tablename__ = "auth_usuario"

    # PK y FK simultaneas: la fila existe si y solo si el usuario existe, y
    # un usuario tiene a lo sumo una fila de auth.
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    # argon2id: ~95 caracteres para el hash completo con sal y parametros.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # SHA-256 hex de un token de 48 bytes random. 64 caracteres alcanzan.
    # unique=True: dos usuarios no pueden terminar con el mismo hash de
    # refresh activo. Postgres permite múltiples NULL en una columna unique,
    # así que no molesta a las cuentas sin sesión activa (logout).
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), unique=True)
    refresh_token_expira_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    ultimo_acceso_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
