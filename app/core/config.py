"""Lectura de la configuración desde el entorno (.env)."""

import os

from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "Falta la variable de entorno DATABASE_URL. "
            "Copiá env.example a .env y completala."
        )
    return url


DATABASE_URL: str = os.getenv("DATABASE_URL", "")

SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() in ("1", "true", "yes")
