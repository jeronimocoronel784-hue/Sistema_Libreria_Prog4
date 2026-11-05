"""Rutas de autenticación (``/auth``).

El grupo de rutas **abierto** de ``main.py`` monta este router: el catálogo es
público y ``/auth`` tiene que poder usarse para iniciarla. ``/auth/yo`` y
``/auth/cambiar-password`` exigen sesión por dentro (``get_usuario_actual``),
pero **no** el control de cambio obligatorio: si lo exigieran, un usuario con
contraseña provisoria no podría cambiar la clave nunca (RN-06).

El token viaja **sólo** en la cookie ``access_token``: HttpOnly, SameSite=Lax,
Max-Age igual a la duración del token y ``Secure`` configurable. El cuerpo de
la respuesta no lo trae.
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.dependencies import UsuarioActual, get_usuario_actual
from app.modules.usuarios import service
from app.modules.usuarios.schemas import (
    CambioPassword,
    LoginCrear,
    LoginRespuesta,
    RegistroCrear,
    YoRead,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])

NOMBRE_COOKIE = "access_token"


def get_usuarios_uow(
    session: AsyncSession = Depends(get_session),
) -> UsuariosUnitOfWork:
    """Construye el Unit of Work de acceso con la sesión de la petición.

    El router **construye** el UoW; el servicio lo abre con ``async with`` y
    nunca lo construye.
    """
    return UsuariosUnitOfWork(session)


def _ip(request: Request) -> str:
    """Dirección del cliente, para el límite de intentos de login."""
    if request.client is None:
        return "desconocida"
    return request.client.host


@router.post("/registro", status_code=201)
async def registro(
    data: RegistroCrear,
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """Auto-registro: crea el usuario, su rol CLIENTE y su ficha de cliente.

    201 con los tres creados; 409 si el correo ya existe (de usuario o de
    cliente); 422 si el cuerpo no cumple el contrato.
    """
    usuario = await service.registrar(uow, data)
    return {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "mensaje": "Registro exitoso.",
    }


@router.post("/login", response_model=LoginRespuesta)
async def login(
    data: LoginCrear,
    request: Request,
    response: Response,
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """Login con cookie.

    200 con la cookie ``access_token``; 401 con el mismo cuerpo exista o no el
    correo; 422 si el cuerpo no cumple el contrato; 429 con ``Retry-After`` si
    se superó el límite de intentos.
    """
    settings = get_settings()
    session_maker = request.app.state.session_factory
    hash_ficticio = request.app.state.hash_ficticio

    usuario, _roles, token = await service.autenticar(
        uow,
        session_maker,
        data,
        ip=_ip(request),
        hash_ficticio=hash_ficticio,
    )

    expira_en = settings.TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key=NOMBRE_COOKIE,
        value=token,
        max_age=expira_en,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    return {
        "mensaje": "Sesión iniciada",
        "debe_cambiar_password": usuario.debe_cambiar_password,
        "expira_en_segundos": expira_en,
    }


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Cierra la sesión borrando la cookie. 200 siempre."""
    response.delete_cookie(key=NOMBRE_COOKIE, path="/")
    return {"mensaje": "Sesión cerrada"}


@router.get("/yo", response_model=YoRead)
async def yo(
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """El usuario, sus roles **vigentes** en la base y los que dice el token.

    200 con sesión; 401 sin cookie, con token inválido o vencido, o si el
    usuario no existe o está inactivo.
    """
    roles_vigentes = await service.roles_vigentes(uow, actual.usuario.id)
    roles_del_token = list(actual.claims.get("roles") or [])
    usuario = actual.usuario
    return {
        "usuario": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "activo": usuario.activo,
            "debe_cambiar_password": usuario.debe_cambiar_password,
        },
        "roles_vigentes": roles_vigentes,
        "roles_del_token": roles_del_token,
    }


@router.post("/cambiar-password")
async def cambiar_password(
    data: CambioPassword,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """Cambia la contraseña del usuario autenticado.

    200; 401 si la contraseña actual no es correcta; 422 si el cuerpo no
    cumple el contrato. La sesión abierta sigue sirviendo: cambiar la
    contraseña no invalida las sesiones ni emite un token nuevo.
    """
    await service.cambiar_password(uow, actual.usuario, data)
    return {"mensaje": "Contraseña actualizada."}
