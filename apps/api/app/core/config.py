"""Configuración de entorno.

Nada de esto se hardcodea en otro lado. Si falta una variable obligatoria, el
proceso no arranca: arrancar con configuración incompleta es peor que no
arrancar.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _con_driver_async(url: str) -> str:
    """Railway (y la mayoría de proveedores) da la URL como
    `postgresql://...` o `postgres://...`; `create_async_engine` necesita
    el driver asyncpg explícito en el scheme."""
    for prefijo in ("postgresql://", "postgres://"):
        if url.startswith(prefijo):
            return "postgresql+asyncpg://" + url[len(prefijo) :]
    return url


def _raiz_monorepo() -> Path:
    """Busca hacia arriba el directorio que tiene el `.env.example`.

    Los .env viven en la raíz del monorepo pero los comandos se corren desde
    apps/api, así que no sirve el cwd. Tampoco sirve contar niveles fijos desde
    __file__: en la imagen de Docker el código queda en /srv/app/... y no hay
    tantos padres. Si no aparece (que es el caso dentro del contenedor, donde
    la configuración llega por variables de entorno), se usa el cwd y listo.
    """
    for directorio in Path(__file__).resolve().parents:
        if (directorio / ".env.example").is_file():
            return directorio
    return Path.cwd()


RAIZ_MONOREPO = _raiz_monorepo()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(RAIZ_MONOREPO / ".env", RAIZ_MONOREPO / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Aplicación ----------
    app_name: str = "rendimiento-api"
    app_env: Literal["local", "test", "prod"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    tz: str = "America/Bogota"
    # Orígenes permitidos, separados por coma.
    cors_origins: str = "http://localhost:3000"

    # ---------- Base de datos ----------
    # Dos formas de configurar la conexión, a elección: `DATABASE_URL` sola
    # (lo que da Railway y la mayoría de proveedores al crear el Postgres),
    # o las partes sueltas (lo que arma docker-compose en dev local). Si
    # llega DATABASE_URL, gana ella entera y las partes no hacen falta.
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_db: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None

    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    @model_validator(mode="after")
    def _validar_conexion_db(self) -> Self:
        if self.database_url_override:
            return self
        faltantes = [
            nombre
            for nombre, valor in (
                ("POSTGRES_HOST", self.postgres_host),
                ("POSTGRES_DB", self.postgres_db),
                ("POSTGRES_USER", self.postgres_user),
                ("POSTGRES_PASSWORD", self.postgres_password),
            )
            if not valor
        ]
        if faltantes:
            raise ValueError(
                "Definí DATABASE_URL, o si no, todas estas: " + ", ".join(faltantes)
            )
        return self

    # ---------- Seed del usuario único ----------
    # Las credenciales son fase 2. Acá solo el nombre, que es lo que la fase 1
    # necesita para que las tablas con usuario_id NOT NULL se puedan sembrar.
    seed_usuario_nombre: str = Field(min_length=1)

    # Email y password del usuario único. El seed los usa para crear la fila
    # de `auth_usuario`. Default vacio a proposito: el api arranca sin ellos
    # (no son runtime), pero el seed aborta con error claro si estan vacios.
    seed_usuario_email: str = ""
    seed_usuario_password: str = ""

    # ---------- Auth ----------
    # Clave de firma del JWT. En Fase 3 con un solo usuario alcanza HS256;
    # cuando haya mas de un issuer se cambia a RS256 sin tocar el codigo de
    # los routers, solo este setting y `core/seguridad.py`. Default vacio:
    # `core/seguridad.py` aborta al usarlo si el codigo llega a importarlo
    # en un entorno sin clave (ej. tests sin auth).
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    # Access corto + refresh rotativo: el refresh existe justamente para que
    # el access pueda ser de vida corta sin friccionar al usuario.
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    def dsn(self, database: str) -> str:
        """URL de conexión a una base arbitraria del mismo servidor.

        Solo tiene sentido con las partes sueltas: `_validar_conexion_db`
        garantiza que si no hay `database_url_override`, estas 3 no son
        `None`. `test_database_url` (dev/CI, siempre con partes sueltas)
        es el único llamador real."""
        assert self.postgres_user is not None
        assert self.postgres_password is not None
        assert self.postgres_host is not None
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=database,
            )
        )

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return _con_driver_async(self.database_url_override)
        assert self.postgres_db is not None
        return self.dsn(self.postgres_db)

    @property
    def test_database_url(self) -> str:
        """Base separada para tests. Se crea y se destruye en cada corrida.
        Siempre por partes sueltas (nunca corre contra `DATABASE_URL` de
        Railway): tests locales/CI configuran Postgres con las 5 vars."""
        assert self.postgres_db is not None
        return self.dsn(f"{self.postgres_db}_test")

    @property
    def cors_origins_lista(self) -> list[str]:
        return [
            origen.strip() for origen in self.cors_origins.split(",") if origen.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
