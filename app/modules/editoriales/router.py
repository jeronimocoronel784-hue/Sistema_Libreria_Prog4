"""Rutas del módulo editoriales.

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
from app.modules.editoriales import service
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialRead,
    EditorialUpdate,
)
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork

router = APIRouter(prefix="/editoriales", tags=["editoriales"])
router_admin = APIRouter(prefix="/editoriales", tags=["editoriales"])


def get_editoriales_uow(
    session: AsyncSession = Depends(get_session),
) -> EditorialesUnitOfWork:
    """Construye el Unit of Work de editoriales con la sesión de la petición."""
    return EditorialesUnitOfWork(session)


@router.get("/", response_model=Page[EditorialRead])
async def listar_editoriales(
    params: PageParamsDep,
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> dict:
    """Listado paginado de editoriales. 200; 422 si el paging no cumple el contrato."""
    pagina = await service.listar(uow, params)
    return pagina.model_dump()


@router.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(
    editorial_id: int,
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> dict:
    """Editorial por id. 200; 404 si no existe; 422 si el id no es entero."""
    editorial = await service.obtener(uow, editorial_id)
    return editorial.model_dump()


@router.get("/{editorial_id}/libros", response_model=Page[LibroResumen])
async def libros_de_editorial(
    editorial_id: int,
    params: PageParamsDep,
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> dict:
    """Libros de la editorial, paginados. 200; 404 si la editorial no existe."""
    pagina = await service.libros_de_editorial(uow, editorial_id, params)
    return pagina.model_dump()


@router_admin.post("/", response_model=EditorialRead, status_code=201)
async def crear_editorial(
    data: EditorialCreate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> dict:
    """Alta de editorial (sólo ADMIN). 201; 409 si el nombre ya existe; 422."""
    editorial = await service.crear(uow, data)
    return editorial.model_dump()


@router_admin.patch("/{editorial_id}", response_model=EditorialRead)
async def actualizar_editorial(
    editorial_id: int,
    data: EditorialUpdate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> dict:
    """PATCH parcial de la editorial (sólo ADMIN). 200; 404; 409; 422."""
    editorial = await service.actualizar(uow, editorial_id, data)
    return editorial.model_dump()
