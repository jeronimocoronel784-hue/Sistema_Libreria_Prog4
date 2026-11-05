"""Rutas del módulo géneros.

Dos routers:

- ``router``: lecturas, que son **públicas** (el catálogo es público).
- ``router_admin``: escrituras, que van en el grupo **protegido** y exigen rol
  ADMIN.
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActual, requiere_rol
from app.core.paginacion import Page, PageParamsDep
from app.modules.common.schemas import LibroResumen
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead, GeneroUpdate
from app.modules.generos.unit_of_work import GenerosUnitOfWork

router = APIRouter(prefix="/generos", tags=["generos"])
router_admin = APIRouter(prefix="/generos", tags=["generos"])


def get_generos_uow(
    session: AsyncSession = Depends(get_session),
) -> GenerosUnitOfWork:
    """Construye el Unit of Work de géneros con la sesión de la petición."""
    return GenerosUnitOfWork(session)


@router.get("/", response_model=Page[GeneroRead])
async def listar_generos(
    params: PageParamsDep,
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> dict:
    """Listado paginado de géneros. 200; 422 si el paging no cumple el contrato."""
    pagina = await service.listar(uow, params)
    return pagina.model_dump()


@router.get("/{genero_id}", response_model=GeneroRead)
async def obtener_genero(
    genero_id: int,
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> dict:
    """Género por id. 200; 404 si no existe; 422 si el id no es entero."""
    genero = await service.obtener(uow, genero_id)
    return genero.model_dump()


@router.get("/{genero_id}/libros", response_model=Page[LibroResumen])
async def libros_del_genero(
    genero_id: int,
    params: PageParamsDep,
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> dict:
    """Libros del género, paginados. 200; 404 si el género no existe."""
    pagina = await service.libros_del_genero(uow, genero_id, params)
    return pagina.model_dump()


@router_admin.post("/", response_model=GeneroRead, status_code=201)
async def crear_genero(
    data: GeneroCreate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> dict:
    """Alta de género (sólo ADMIN). 201; 409 si el nombre ya existe; 422."""
    genero = await service.crear(uow, data)
    return genero.model_dump()


@router_admin.patch("/{genero_id}", response_model=GeneroRead)
async def actualizar_genero(
    genero_id: int,
    data: GeneroUpdate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> dict:
    """PATCH parcial del género (sólo ADMIN). 200; 404; 409; 422."""
    genero = await service.actualizar(uow, genero_id, data)
    return genero.model_dump()
