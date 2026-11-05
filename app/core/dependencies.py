"""Dependencias compartidas de FastAPI.

Identidad y autorización:

- ``get_usuario_actual`` resuelve la sesión desde la cookie y responde 401 si no
  hay cookie, el token es inválido/vencido, el usuario no existe o está
  inactivo. Lee el token **sólo** de ``request.cookies["access_token"]``;
  nunca de la cabecera ``Authorization``.
- ``requiere_rol(*roles)`` responde 403 y consulta ``asignacion_rol`` **en la
  base en cada petición** (RN-04): rol vigente = fila no revocada y sin
  vencer. Los roles del token son informativos y **nunca** autorizan.
- ``exigir_password_al_dia`` responde 403 mientras ``debe_cambiar_password``
  esté activo (RN-06). Se monta **una sola vez** en el grupo protegido de
  ``main.py``: FastAPI suma dependencias y no las resta.

Las dependencias de usuario actual y de rol reciben **la misma sesión** que el
Unit of Work: sin esa unificación, cada petición autenticada tomaría dos
conexiones del pool.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import verificar_token
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.usuarios.repository import AsignacionRolRepository

# Dependencia de sesión lista para usar en los routers:
#     async def handler(session: AsyncSession = SessionDep) -> ...
SessionDep = Depends(get_session)

NOMBRE_COOKIE = "access_token"
MENSAJE_SIN_SESION = "No hay una sesión válida."
HTTP_401 = 401

# Literal a propósito: el nombre del status cambió entre versiones de Starlette.
HTTP_403 = 403
MENSAJE_SIN_PERMISO = "No tenés permiso para realizar esta operación."
MENSAJE_CAMBIO_PENDIENTE = (
    "Tenés que cambiar la contraseña provisoria antes de usar esta ruta."
)


@dataclass(frozen=True)
class UsuarioActual:
    """Identidad resuelta de la petición: el usuario y los claims del token.

    ``claims`` expone ``roles`` (informativos) para ``GET /auth/yo``. La
    autorización real se consulta en la base en cada petición (RN-04);
    ``requiere_rol`` nunca confía en estos roles.
    """

    usuario: Usuario
    claims: dict[str, Any]


def _sin_sesion() -> HTTPException:
    """401 uniforme: no se distingue por qué falló la sesión."""
    return HTTPException(status_code=HTTP_401, detail=MENSAJE_SIN_SESION)


async def get_usuario_actual(
    request: Request,
    session: AsyncSession = SessionDep,
) -> UsuarioActual:
    """Resuelve el usuario de la cookie ``access_token`` o lanza 401.

    No acepta ``Authorization: Bearer``: el token viaja **sólo** en la cookie
    HttpOnly.
    """
    token = request.cookies.get(NOMBRE_COOKIE)
    if not token:
        raise _sin_sesion()

    claims = verificar_token(token)
    if claims is None:
        raise _sin_sesion()

    try:
        usuario_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise _sin_sesion() from None

    usuario = await session.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise _sin_sesion()

    return UsuarioActual(usuario=usuario, claims=claims)


UsuarioActualDep = Depends(get_usuario_actual)


def requiere_rol(*roles: str) -> Callable[..., Any]:
    """Factory de dependencia: 403 si el usuario no tiene alguno de ``roles``.

    La decisión se toma con los roles **vigentes en la base**, consultados en
    **cada** petición (RN-04): no se leen del token. Revocar un rol le quita el
    permiso a una sesión ya abierta sin esperar a que venza el JWT.

    Uso: ``actual: UsuarioActual = Depends(requiere_rol("ADMIN"))``. Nunca se
    usa como ``dependencies=[...]`` del grupo: el grupo ya exige sesión y el
    cambio obligatorio; el rol es una decisión por ruta.
    """
    esperados = frozenset(roles)

    async def _verificar_rol(
        actual: UsuarioActual = UsuarioActualDep,
        session: AsyncSession = SessionDep,
    ) -> UsuarioActual:
        # Se consulta la tabla en cada petición: el claim ``roles`` del token es
        # informativo (lo expone /auth/yo), no una fuente de autorización.
        vigentes = await AsignacionRolRepository(session, AsignacionRol).roles_vigentes(
            actual.usuario.id
        )
        if esperados.isdisjoint(vigentes):
            raise HTTPException(status_code=HTTP_403, detail=MENSAJE_SIN_PERMISO)
        return actual

    return _verificar_rol


async def exigir_password_al_dia(
    actual: UsuarioActual = UsuarioActualDep,
) -> None:
    """403 mientras el cambio de contraseña obligatorio siga pendiente (RN-06).

    ``get_usuario_actual`` ya se ejecutó aquí: sin sesión la respuesta es 401,
    no 403. Este control se monta **una sola vez** en el grupo protegido de
    ``main.py``; el grupo abierto (``/auth`` y ``/health``) no lo lleva, para
    que el afectado pueda loguearse y cambiar la clave.
    """
    if actual.usuario.debe_cambiar_password:
        raise HTTPException(status_code=HTTP_403, detail=MENSAJE_CAMBIO_PENDIENTE)


# Alias listos para usar como valor por defecto de un parámetro.
AdminDep = Depends(requiere_rol("ADMIN"))
VendedorDep = Depends(requiere_rol("ADMIN", "VENDEDOR"))
AutenticadoDep = UsuarioActualDep
