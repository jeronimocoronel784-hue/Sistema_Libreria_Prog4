"""Primitivas de seguridad: hash de contraseñas y token firmado.

Reglas duras que este módulo implementa:

- bcrypt corre **fuera del bucle de eventos** (``asyncio.to_thread``) y bajo un
  semáforo configurable (``BCRYPT_MAX_CONCURRENT_HASHES``): el costo sale de
  ``Settings`` y nunca se escribe en el código.
- El hash se calcula **antes** de abrir la transacción: adentro, la conexión
  quedaría tomada los ~300 ms que tarda bcrypt sin usar la base.
- El límite de 72 bytes vive en los **contratos**, no acá: son bytes y no
  caracteres (una «ñ» ocupa dos). bcrypt no mira más allá de los 72 bytes y
  desde la versión 5 rechaza con una excepción lo que pasa de ahí, así que sin
  el límite en el contrato una contraseña larga daría un 500 en lugar de un 422.
- El token se firma con la clave del entorno (sin default) y lleva ``sub``,
  ``iat``, ``exp`` y los roles vigentes al emitirlo. Los roles del token son
  **informativos**: la autorización real se consulta en la base en cada
  petición (RN-04).
- ``verificar_token`` **no levanta**: devuelve ``None`` y el llamador decide el
  401.
- El **hash ficticio** se calcula una sola vez al arrancar: sirve para
  verificar contra algo cuando el correo no existe, y que el login tarde lo
  mismo exista o no el correo (RN-08).
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"

# Lo que se hashea para tener un hash de referencia. No es la contraseña de
# nadie: sólo sirve para igualar el tiempo de respuesta del login.
SEMILLA_FICTICIA = b"libreria-contrasena-ficticia"

# bcrypt mira como máximo 72 bytes. Es un límite de bytes, no de caracteres.
MAX_BYTES_PASSWORD = 72

_semaforo: asyncio.Semaphore | None = None
_hash_ficticio: str | None = None


def _obtener_semaforo() -> asyncio.Semaphore:
    """El semáforo que limita cuántos hashes corren a la vez."""
    global _semaforo
    if _semaforo is None:
        limite = max(1, get_settings().BCRYPT_MAX_CONCURRENT_HASHES)
        _semaforo = asyncio.Semaphore(limite)
    return _semaforo


def init_seguridad() -> None:
    """Prepara el hash ficticio del login. Se llama **una vez** en el lifespan.

    Calcularlo cuesta lo mismo que un hash de contraseña (~300 ms con el coste
    de la configuración), y no tiene sentido pagarlo en cada login: se hace una
    sola vez al arrancar la aplicación.
    """
    global _hash_ficticio
    if _hash_ficticio is None:
        _hash_ficticio = bcrypt.hashpw(
            SEMILLA_FICTICIA, bcrypt.gensalt(rounds=get_settings().BCRYPT_ROUNDS)
        ).decode("utf-8")


def hash_ficticio() -> str:
    """El hash contra el que se verifica cuando el correo no existe (RN-08)."""
    if _hash_ficticio is None:
        init_seguridad()
    assert _hash_ficticio is not None  # para el type checker
    return _hash_ficticio


async def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de ``password``, calculado fuera del bucle."""

    def _hash() -> str:
        salt = bcrypt.gensalt(rounds=get_settings().BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    async with _obtener_semaforo():
        return await asyncio.to_thread(_hash)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash. Nunca levanta: falla con ``False``."""

    def _verify() -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except (ValueError, TypeError):
            # Hash malformado, contraseña de más de 72 bytes, etc.
            return False

    async with _obtener_semaforo():
        return await asyncio.to_thread(_verify)


def crear_token(
    sub: str,
    roles: Sequence[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Emite un JWT firmado con ``sub``, ``iat``, ``exp`` y, si se pasan, los roles.

    Los roles son **informativos**: la autorización real se consulta en la base
    en cada petición (RN-04). Sirven para que ``GET /auth/yo`` muestre
    "lo que dice el token" junto a los roles vigentes.
    """
    ahora = datetime.now(timezone.utc)
    duracion = expires_delta or timedelta(minutes=get_settings().TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": sub,
        "iat": ahora.timestamp(),
        "exp": (ahora + duracion).timestamp(),
    }
    if roles is not None:
        payload["roles"] = list(roles)

    return jwt.encode(payload, get_settings().SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str) -> dict[str, Any] | None:
    """Devuelve los claims del token o ``None`` si no es válido.

    Rechaza (sin levantar) tokens vencidos, con firma inválida o sin alguno de
    los claims obligatorios ``sub``, ``iat`` y ``exp``.
    """
    try:
        return jwt.decode(
            token,
            get_settings().SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
    except jwt.PyJWTError:
        return None
