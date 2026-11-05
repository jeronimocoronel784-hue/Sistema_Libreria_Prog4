"""Rutas del módulo libros.

Dos routers:

- ``router``: lecturas del catálogo, que son **públicas**.
- ``router_admin``: escrituras (alta, PATCH, baja, reposición y movimientos),
  que van en el grupo **protegido** y exigen rol ADMIN.
"""

from fastapi import APIRouter, Depends, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActual, requiere_rol
from app.core.paginacion import Page, PageParamsDep
from app.modules.libros import service
from app.modules.libros.models import Libro
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetalle,
    LibroEnLista,
    LibroUpdate,
    MovimientoRead,
    Reposicion,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork

router = APIRouter(prefix="/libros", tags=["libros"])
router_admin = APIRouter(prefix="/libros", tags=["libros"])


def get_libros_uow(
    session: AsyncSession = Depends(get_session),
) -> LibrosUnitOfWork:
    """Construye el Unit of Work de libros con la sesión de la petición."""
    return LibrosUnitOfWork(session)


def _detalle(libro: Libro) -> dict:
    """Arma el detalle del libro.

    El diccionario se arma a mano (y no con ``model_dump``) porque las
    relaciones son bidireccionales: ``libro.autorias[i].libro`` volvería al
    libro y el volcado sería recursivo.
    """
    return {
        "id": libro.id,
        "isbn": libro.isbn,
        "titulo": libro.titulo,
        "precio": libro.precio,
        "stock": libro.stock,
        "editorial_id": libro.editorial_id,
        "genero_id": libro.genero_id,
        "editorial": (
            {
                "id": libro.editorial.id,
                "nombre": libro.editorial.nombre,
                "pais": libro.editorial.pais,
            }
            if libro.editorial is not None
            else None
        ),
        "genero": (
            {"id": libro.genero.id, "nombre": libro.genero.nombre}
            if libro.genero is not None
            else None
        ),
        "autores": [
            {
                "autor_id": a.autor_id,
                "rol": a.rol,
                "orden": a.orden,
                "autor": (
                    {
                        "id": a.autor.id,
                        "nombre": a.autor.nombre,
                        "nacionalidad": a.autor.nacionalidad,
                    }
                    if a.autor is not None
                    else {"id": a.autor_id, "nombre": "", "nacionalidad": None}
                ),
            }
            for a in sorted(libro.autorias, key=lambda x: x.orden)
        ],
    }


def _en_lista(libro: Libro) -> dict:
    """Arma la fila del listado (sin relaciones que no se usan)."""
    return {
        "id": libro.id,
        "isbn": libro.isbn,
        "titulo": libro.titulo,
        "precio": libro.precio,
        "stock": libro.stock,
        "editorial_id": libro.editorial_id,
        "genero_id": libro.genero_id,
        "editorial": (
            {
                "id": libro.editorial.id,
                "nombre": libro.editorial.nombre,
                "pais": libro.editorial.pais,
            }
            if libro.editorial is not None
            else None
        ),
        "genero": (
            {"id": libro.genero.id, "nombre": libro.genero.nombre}
            if libro.genero is not None
            else None
        ),
    }


@router.get("/", response_model=Page[LibroEnLista])
async def listar_libros(
    params: PageParamsDep,
    titulo: str | None = None,
    genero_id: int | None = None,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> dict:
    """Catálogo paginado, con filtro por título y género.

    200; 422 si el paging no cumple el contrato. Los libros dados de baja no
    aparecen. La búsqueda por título usa parámetro ligado.
    """
    pagina = await service.listar(uow, params, titulo=titulo, genero_id=genero_id)
    return pagina.model_dump()


@router.get("/{libro_id}", response_model=LibroDetalle)
async def obtener_libro(
    libro_id: int,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> dict:
    """Detalle del libro con su editorial, género y autores.

    200; 404 si no existe (o está dado de baja); 422 si el id no es entero.
    """
    libro = await service.obtener_detalle(uow, libro_id)
    return _detalle(libro)


@router_admin.post("/", response_model=LibroDetalle, status_code=201)
async def crear_libro(
    data: LibroCreate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> dict:
    """Alta de libro con autores y stock inicial (sólo ADMIN).

    201; 409 si el ISBN ya está en uso entre los vigentes o si la editorial, el
    género o el autor no existen; 422 si el cuerpo no cumple el contrato.
    """
    creado = await service.crear(uow, data, usuario_id=admin.usuario.id)
    libro = await service.obtener_detalle(uow, creado.id)
    return _detalle(libro)


@router_admin.patch("/{libro_id}", response_model=LibroDetalle)
async def actualizar_libro(
    libro_id: int,
    data: LibroUpdate,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> dict:
    """PATCH parcial del libro: sólo título y precio (sólo ADMIN).

    200; 404; 409; 422. Un PATCH con ``stock`` es 422: el stock no se edita
    (RN-11).
    """
    libro = await service.actualizar(uow, libro_id, data)
    return _detalle(libro)


@router_admin.delete("/{libro_id}", status_code=204)
async def dar_de_baja_libro(
    libro_id: int,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> Response:
    """Baja lógica del libro (sólo ADMIN). 204; 404 si no existe."""
    await service.dar_de_baja(uow, libro_id)
    return Response(status_code=204)


@router_admin.post("/{libro_id}/reponer", response_model=LibroDetalle)
async def reponer_stock(
    libro_id: int,
    data: Reposicion,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> dict:
    """Reposición de stock (sólo ADMIN). 200; 404; 409; 422.

    El stock sube y queda un movimiento: es la única forma de cambiarlo
    (RN-11).
    """
    await service.reponer(
        uow, libro_id, data.cantidad, usuario_id=admin.usuario.id
    )
    libro = await service.obtener_detalle(uow, libro_id)
    return _detalle(libro)


@router_admin.get("/{libro_id}/movimientos", response_model=Page[MovimientoRead])
async def movimientos_del_libro(
    libro_id: int,
    params: PageParamsDep,
    admin: UsuarioActual = Depends(requiere_rol("ADMIN")),
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> dict:
    """Movimientos de stock del libro, paginados (sólo ADMIN). 200; 404; 422."""
    pagina = await service.movimientos(uow, libro_id, params)
    return pagina.model_dump()
