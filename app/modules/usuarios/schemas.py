"""Contratos del módulo de acceso.

Reglas duras que este módulo implementa:

- **Los contratos de entrada rechazan los campos que no declaran**
  (``extra="forbid"``): de ese modo nadie se registra con un rol, ni edita el
  stock por PATCH, ni se manda un ``password_hash``.
- **Ninguna respuesta incluye ``password_hash``**.
- Todo campo que termina en bcrypt acepta como máximo **72 bytes**: son bytes
  y no caracteres (una «ñ» ocupa dos). bcrypt no mira más allá, así que sin el
  límite una contraseña larga daría un 500 en lugar de un 422.
- El vencimiento de un rol llega **con zona horaria y en el futuro**: una fecha
  sin zona es ambigua (¿la hora de quién?) y una que ya pasó no choca con nada
  guardado; las dos son 422, no 409.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, field_validator
from sqlmodel import Field, SQLModel

from app.core.security import MAX_BYTES_PASSWORD
from app.modules.common.schemas import EntradaBase

Rol = Literal["ADMIN", "VENDEDOR", "CLIENTE"]

MENSAJE_PASSWORD_LARGA = (
    "La contraseña no puede superar los 72 bytes (es el límite de bcrypt)."
)


def _validar_password(password: str) -> str:
    """Límite de 72 bytes de bcrypt (bytes, no caracteres)."""
    if len(password.encode("utf-8")) > MAX_BYTES_PASSWORD:
        raise ValueError(MENSAJE_PASSWORD_LARGA)
    return password


class RegistroCrear(EntradaBase):
    """Auto-registro de un cliente en la web (RN-02)."""

    email: str = Field(max_length=320)
    nombre: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _password_corta(cls, v: str) -> str:
        return _validar_password(v)


class LoginCrear(EntradaBase):
    """Credenciales del login."""

    email: str = Field(max_length=320)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _password_corta(cls, v: str) -> str:
        return _validar_password(v)


class UsuarioCrear(EntradaBase):
    """Alta de personal con contraseña provisoria (``POST /usuarios``)."""

    email: str = Field(max_length=320)
    nombre: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _password_corta(cls, v: str) -> str:
        return _validar_password(v)


class CambioPassword(EntradaBase):
    """Cambio de contraseña: la actual y la nueva."""

    password_actual: str = Field(min_length=1)
    password_nueva: str = Field(min_length=1)

    @field_validator("password_actual", "password_nueva")
    @classmethod
    def _password_corta(cls, v: str) -> str:
        return _validar_password(v)


class RolAsignar(EntradaBase):
    """Asignación de un rol, con vencimiento opcional."""

    rol: Rol
    desde: AwareDatetime | None = None
    vence_en: AwareDatetime | None = None

    @field_validator("vence_en")
    @classmethod
    def _vencimiento_futuro(cls, v: AwareDatetime | None) -> AwareDatetime | None:
        if v is None:
            return v
        if v <= datetime.now(timezone.utc):
            raise ValueError("La fecha de vencimiento tiene que ser futura.")
        return v


# --- Salida ------------------------------------------------------------------


class UsuarioRead(SQLModel):
    """Usuario que se devuelve. **Nunca** incluye ``password_hash``."""

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool


class LoginRespuesta(SQLModel):
    """Respuesta del login. El token viaja en la cookie, no en el cuerpo."""

    mensaje: str
    debe_cambiar_password: bool
    expira_en_segundos: int


class YoRead(SQLModel):
    """``GET /auth/yo``: el usuario, sus roles vigentes y los que dice el token."""

    usuario: UsuarioRead
    roles_vigentes: list[str]
    roles_del_token: list[str]


class RolRead(SQLModel):
    """Asignación de rol (incluye las revocadas: la fila no se borra nunca)."""

    id: int
    usuario_id: int
    rol: str
    desde: datetime
    vence_en: datetime | None = None
    revocada_en: datetime | None = None
    otorgada_por: str | None = None


class EventoRead(SQLModel):
    """Línea del historial de seguridad."""

    id: int
    cuando: datetime
    actor: str
    accion: str
