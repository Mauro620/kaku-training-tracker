"""Configuración de entorno.

Nada de esto se hardcodea en otro lado. Si falta una variable obligatoria, el
proceso no arranca: arrancar con configuración incompleta es peor que no
arrancar.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Aplicación ----------
    app_name: str = "rendimiento-api"
    app_env: Literal["local", "test", "prod"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    tz: str = "America/Bogota"

    # ---------- Base de datos ----------
    # Las partes son la fuente de verdad; la URL se deriva. Tener las dos cosas
    # en el entorno es garantía de que un día no coincidan.
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str

    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # ---------- Seed del usuario único ----------
    # Las credenciales son fase 2. Acá solo el nombre, que es lo que la fase 1
    # necesita para que las tablas con usuario_id NOT NULL se puedan sembrar.
    seed_usuario_nombre: str = Field(min_length=1)

    def _dsn(self, database: str) -> str:
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
        return self._dsn(self.postgres_db)

    @property
    def test_database_url(self) -> str:
        """Base separada para tests. Se crea y se destruye en cada corrida."""
        return self._dsn(f"{self.postgres_db}_test")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
