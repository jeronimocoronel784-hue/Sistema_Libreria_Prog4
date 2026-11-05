"""Configuración de la aplicación (pydantic-settings).

Reglas duras que este módulo implementa:

- La dirección de la base se **arma** en el código a partir de las variables
  sueltas ``POSTGRES_USER``, ``POSTGRES_PASSWORD``, ``POSTGRES_DB``,
  ``POSTGRES_HOST`` y ``POSTGRES_PORT``, con el driver ``postgresql+asyncpg``.
- Ni la clave de firma del token ni la contraseña de la base tienen **valor por
  defecto**: si faltan, la aplicación no arranca. La clave de firma es el
  secreto más importante del sistema (quien la tenga fabrica un token válido
  para cualquier usuario) y una clave inventada al arrancar tampoco sirve:
  cambia en cada reinicio y con dos procesos cada uno rechaza los tokens del
  otro.
- El coste de bcrypt, el tamaño del pool y la duración del token son
  **configuración**, no constantes en el código.
- ``env.example`` lista todas las variables y ningún secreto.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

DRIVER = "postgresql+asyncpg"


class Settings(BaseSettings):
    """Configuración leída del entorno o de un ``.env`` que no se versiona."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- Base de datos -------------------------------------------------------
    # Sin valores por defecto: si faltan, la aplicación no arranca.
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    # Opcional: esquema de PostgreSQL donde viven las tablas. Vacío = el
    # esquema por defecto de la búsqueda (``public``).
    POSTGRES_SCHEMA: str | None = None

    # --- Secretos ------------------------------------------------------------
    # La clave de firma del token: sin valor por defecto, nunca en el código.
    SECRET_KEY: str

    # --- bcrypt --------------------------------------------------------------
    # El coste sube con los años: va en la configuración, no fijo en el código.
    BCRYPT_ROUNDS: int = 12
    # Cuántos hashes pueden correr a la vez (bcrypt tarda ~300 ms y satura el
    # bucle de eventos si se deixa libre).
    BCRYPT_MAX_CONCURRENT_HASHES: int = 4

    # --- Token y cookie ------------------------------------------------------
    TOKEN_EXPIRE_MINUTES: int = 30
    # `Secure` depende de cómo se sirva la app: en local por HTTP va en false.
    COOKIE_SECURE: bool = False

    # --- Motor asincrónico ---------------------------------------------------
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    SQL_ECHO: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """URL de la base, armada con el driver asincrónico.

        La contraseña y el usuario van escapados: pueden traer caracteres que
        rompen la URL (``@``, ``:``, ``/``).
        """
        usuario = quote(self.POSTGRES_USER, safe="")
        clave = quote(self.POSTGRES_PASSWORD, safe="")
        return (
            f"{DRIVER}://{usuario}:{clave}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def connect_args(self) -> dict[str, dict[str, str]]:
        """Argumentos de conexión del motor.

        El esquema, si se indica, se fija con ``server_settings``: es un GUC de
        sesión y PostgreSQL no lo acepta en la URL.
        """
        if not self.POSTGRES_SCHEMA:
            return {}
        return {"server_settings": {"search_path": self.POSTGRES_SCHEMA}}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuración. Se lee una vez por proceso.

    No se instancia al importar el módulo a propósito: el error por variable
    faltante tiene que aparecer al **arrancar** la aplicación, no al importar
    un módulo cualquiera (y que la importación de un módulo que sólo lee
    configuración no rompa las herramientas).
    """
    return Settings()  # type: ignore[call-arg]
