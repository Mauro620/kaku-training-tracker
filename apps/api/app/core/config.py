"""Configuración de entorno.

Nada de esto se hardcodea en otro lado. Si falta una variable obligatoria, el
proceso no arranca: arrancar con configuración incompleta es peor que no
arrancar.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    def dsn(self, database: str) -> str:
        """URL de conexión a una base arbitraria del mismo servidor."""
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
        return self.dsn(self.postgres_db)

    @property
    def test_database_url(self) -> str:
        """Base separada para tests. Se crea y se destruye en cada corrida."""
        return self.dsn(f"{self.postgres_db}_test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
