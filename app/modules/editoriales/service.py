"""Lógica del módulo editoriales.

El servicio recibe el Unit of Work y lo abre con ``async with``; nunca lo
construye (lo hace el router, con una dependencia).
"""

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.paginacion import Page, PageParams
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork

_MSJ_CONFLICTO = "No se pudo guardar la editorial: el nombre ya está en uso."


async def crear(uow: EditorialesUnitOfWork, data: EditorialCreate) -> Editorial:
    """Alta de editorial. La unicidad la garantiza la base (409)."""
    editorial = Editorial(nombre=data.nombre, pais=data.pais)
    try:
        async with uow:
            await uow.editoriales.add(editorial)
    except IntegrityError:
        raise Conflicto(_MSJ_CONFLICTO) from None
    return editorial


async def listar(
    uow: EditorialesUnitOfWork, params: PageParams
) -> Page[Editorial]:
    """Listado paginado de editoriales."""
    async with uow:
        return await uow.editoriales.list_page(params)


async def obtener(uow: EditorialesUnitOfWork, editorial_id: int) -> Editorial:
    """Editorial por id. 404 si no existe."""
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
    if editorial is None:
        raise RecursoNoEncontrado("la editorial", editorial_id)
    return editorial


async def actualizar(
    uow: EditorialesUnitOfWork, editorial_id: int, data: EditorialUpdate
) -> Editorial:
    """PATCH parcial: sólo se aplican los campos enviados."""
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if editorial is None:
            raise RecursoNoEncontrado("la editorial", editorial_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(editorial, campo, valor)
        try:
            await uow.editoriales.update(editorial)
        except IntegrityError:
            raise Conflicto(_MSJ_CONFLICTO) from None
    return editorial


async def libros_de_editorial(
    uow: EditorialesUnitOfWork, editorial_id: int, params: PageParams
) -> Page:
    """Libros de la editorial, paginados. Los dados de baja no aparecen."""
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if editorial is None:
            raise RecursoNoEncontrado("la editorial", editorial_id)
        pagina = await uow.editoriales.listar_libros(editorial_id, params)

    return Page.create(
        items=[
            {
                "id": libro.id,
                "isbn": libro.isbn,
                "titulo": libro.titulo,
                "precio": libro.precio,
                "stock": libro.stock,
            }
            for libro in pagina.items
        ],
        total=pagina.total,
        params=params,
    )
