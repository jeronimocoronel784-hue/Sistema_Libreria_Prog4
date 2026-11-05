"""Lógica del módulo autores.

El servicio recibe el Unit of Work y lo abre con ``async with``; nunca lo
construye (lo hace el router, con una dependencia).
"""

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.paginacion import Page, PageParams
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate
from app.modules.autores.unit_of_work import AutoresUnitOfWork

_MSJ_CONFLICTO = "No se pudo guardar el autor: el nombre ya está en uso."


async def crear(uow: AutoresUnitOfWork, data: AutorCreate) -> Autor:
    """Alta de autor. La unicidad la garantiza la base (409)."""
    autor = Autor(nombre=data.nombre, nacionalidad=data.nacionalidad)
    try:
        async with uow:
            await uow.autores.add(autor)
    except IntegrityError:
        raise Conflicto(_MSJ_CONFLICTO) from None
    return autor


async def listar(uow: AutoresUnitOfWork, params: PageParams) -> Page[Autor]:
    """Listado paginado de autores."""
    async with uow:
        return await uow.autores.list_page(params)


async def obtener(uow: AutoresUnitOfWork, autor_id: int) -> Autor:
    """Autor por id. 404 si no existe."""
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
    if autor is None:
        raise RecursoNoEncontrado("el autor", autor_id)
    return autor


async def actualizar(
    uow: AutoresUnitOfWork, autor_id: int, data: AutorUpdate
) -> Autor:
    """PATCH parcial: sólo se aplican los campos enviados."""
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if autor is None:
            raise RecursoNoEncontrado("el autor", autor_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(autor, campo, valor)
        try:
            await uow.autores.update(autor)
        except IntegrityError:
            raise Conflicto(_MSJ_CONFLICTO) from None
    return autor


async def libros_del_autor(
    uow: AutoresUnitOfWork, autor_id: int, params: PageParams
) -> Page:
    """Autorías del autor con su libro, paginadas (número fijo de consultas)."""
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if autor is None:
            raise RecursoNoEncontrado("el autor", autor_id)
        pagina = await uow.autores.listar_autorias(autor_id, params)

    return Page.create(
        items=[
            {
                "libro_id": a.libro_id,
                "isbn": a.libro.isbn if a.libro is not None else "",
                "titulo": a.libro.titulo if a.libro is not None else "",
                "rol": a.rol,
                "orden": a.orden,
            }
            for a in pagina.items
        ],
        total=pagina.total,
        params=params,
    )
