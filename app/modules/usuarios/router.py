"""Rutas de administración de personal y del historial de seguridad.

``/usuarios`` y ``/eventos`` van en el grupo **protegido**: exigen sesión y
el control de cambio obligatorio de contraseña, y además el rol ADMIN, que se
decide con los roles **vigentes en la base** en cada petición (RN-04).
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActual, requiere_rol
from app.core.paginacion import Page, PageParamsDep
from app.modules.usuarios import service
from app.modules.usuarios.schemas import EventoRead, RolAsignar, RolRead, UsuarioCrear
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
eventos_router = APIRouter(prefix="/eventos", tags=["eventos"])


def get_usuarios_uow(
    session: AsyncSession = Depends(get_session),
) -> UsuariosUnitOfWork:
    """Construye el Unit of Work de acceso con la sesión de la petición."""
    return UsuariosUnitOfWork(session)


@router.post("/", status_code=201)
async def crear_usuario(
    data: UsuarioCrear,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """Alta de personal con contraseña provisoria (sólo ADMIN).

    201; 409 si el correo ya existe; 422 si el cuerpo no cumple el contrato.
    El usuario queda con el cambio de contraseña pendiente.
    """
    usuario = await service.crear_personal(
        uow, data, actor=service.actor_de(admin.usuario)
    )
    return {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "activo": usuario.activo,
        "debe_cambiar_password": usuario.debe_cambiar_password,
    }


@router.get("/{usuario_id}/roles", response_model=list[RolRead])
async def roles_del_usuario(
    usuario_id: int,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> list:
    """Historial de roles del usuario (sólo ADMIN).

    200; 404 si el usuario no existe. Incluye las filas revocadas: revocar
    escribe ``revocada_en`` y la fila no se borra nunca.
    """
    return await service.listar_roles(uow, usuario_id)


@router.post("/{usuario_id}/roles", response_model=RolRead, status_code=201)
async def asignar_rol(
    usuario_id: int,
    data: RolAsignar,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """Asigna un rol con vencimiento opcional (sólo ADMIN).

    201; 404 si el usuario no existe; 409 si el rol ya tiene una asignación
    abierta; 422 si el cuerpo no cumple el contrato (un vencimiento sin zona
    horaria o en el pasado es 422, no 409).
    """
    return await service.asignar_rol(
        uow, usuario_id, data, actor=service.actor_de(admin.usuario)
    )


@router.delete("/{usuario_id}/roles/{rol}", response_model=RolRead)
async def revocar_rol(
    usuario_id: int,
    rol: str,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """Revoca un rol sin borrar la fila (sólo ADMIN).

    200; 404 si el usuario no existe o no tiene ese rol abierto; 409 si un
    administrador intenta revocarse su propio ADMIN o si dejaría al sistema
    sin administradores vigentes.
    """
    return await service.revocar_rol(
        uow, usuario_id, rol, admin=admin.usuario
    )


@eventos_router.get("/", response_model=Page[EventoRead])
async def listar_eventos(
    params: PageParamsDep,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
) -> dict:
    """Historial de seguridad, paginado (sólo ADMIN). 200; 422 si el paging no
    cumple el contrato."""
    pagina = await service.listar_eventos(uow, params)
    return pagina.model_dump()
