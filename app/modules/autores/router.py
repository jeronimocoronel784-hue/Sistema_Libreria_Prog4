"""Rutas del módulo autores.

Dos routers:

- ``router``: lecturas, que son **públicas** (el catálogo es público).
- ``router_admin``: escrituras, que van en el grupo **protegido** y exigen rol
  ADMIN.

El router construye el Unit of Work con una dependencia y se lo pasa al
servicio sin abrirlo.
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActual, requiere_rol
from app.core.paginacion import Page, PageParamsDep
from app.modules.autores import service
from app.modules.autores.schemas import AutorCreate, AutorRead, AutorUpdate
from app.modules.autores.unit_of_work import AutoresUnitOfWork

router = APIRouter(prefix="/autores", tags=["autores"])
router_admin = APIRouter(prefix="/autores", tags=["autores"])


def get_autores_uow(
    session: AsyncSession = Depends(get_session),
) -> AutoresUnitOfWork:
    """Construye el Unit of Work de autores con la sesión de la petición."""
    return AutoresUnitOfWork(session)


@router.get("/", response_model=Page[AutorRead])
async def listar_autores(
    params: PageParamsDep,
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> dict:
    """Listado paginado de autores. 200; 422 si el paging no cumple el contrato."""
    pagina = await service.listar(uow, params)
    return pagina.model_dump()


@router.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(
    autor_id: int,
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> dict:
    """Autor por id. 200; 404 si no existe; 422 si el id no es entero."""
    autor = await service.obtener(uow, autor_id)
    return autor.model_dump()


@router.get("/{autor_id}/libros")
async def libros_del_autor(
    autor_id: int,
    params: PageParamsDep,
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> dict:
    """Libros del autor, paginados. 200; 404 si el autor no existe."""
    pagina = await service.libros_del_autor(uow, autor_id, params)
    return pagina.model_dump()


@router_admin.post("/", response_model=AutorRead, status_code=201)
async def crear_autor(
    data: AutorCreate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> dict:
    """Alta de autor (sólo ADMIN). 201; 409 si el nombre ya existe; 422 si el
    cuerpo no cumple el contrato."""
    autor = await service.crear(uow, data)
    return autor.model_dump()


@router_admin.patch("/{autor_id}", response_model=AutorRead)
async def actualizar_autor(
    autor_id: int,
    data: AutorUpdate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> dict:
    """PATCH parcial del autor (sólo ADMIN). 200; 404; 409; 422."""
    autor = await service.actualizar(uow, autor_id, data)
    return autor.model_dump()
