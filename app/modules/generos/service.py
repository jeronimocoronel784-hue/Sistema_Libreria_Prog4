"""Lógica del módulo géneros.

El servicio recibe el Unit of Work y lo abre con ``async with``; nunca lo
construye (lo hace el router, con una dependencia).
"""

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.paginacion import Page, PageParams
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate, GeneroUpdate
from app.modules.generos.unit_of_work import GenerosUnitOfWork

_MSJ_CONFLICTO = "No se pudo guardar el género: el nombre ya está en uso."


async def crear(uow: GenerosUnitOfWork, data: GeneroCreate) -> Genero:
    """Alta de género. La unicidad la garantiza la base (409)."""
    genero = Genero(nombre=data.nombre)
    try:
        async with uow:
            await uow.generos.add(genero)
    except IntegrityError:
        raise Conflicto(_MSJ_CONFLICTO) from None
    return genero


async def listar(uow: GenerosUnitOfWork, params: PageParams) -> Page[Genero]:
    """Listado paginado de géneros."""
    async with uow:
        return await uow.generos.list_page(params)


async def obtener(uow: GenerosUnitOfWork, genero_id: int) -> Genero:
    """Género por id. 404 si no existe."""
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
    if genero is None:
        raise RecursoNoEncontrado("el género", genero_id)
    return genero


async def actualizar(
    uow: GenerosUnitOfWork, genero_id: int, data: GeneroUpdate
) -> Genero:
    """PATCH parcial: sólo se aplican los campos enviados."""
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if genero is None:
            raise RecursoNoEncontrado("el género", genero_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(genero, campo, valor)
        try:
            await uow.generos.update(genero)
        except IntegrityError:
            raise Conflicto(_MSJ_CONFLICTO) from None
    return genero


async def libros_del_genero(
    uow: GenerosUnitOfWork, genero_id: int, params: PageParams
) -> Page:
    """Libros del género, paginados. Los dados de baja no aparecen."""
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if genero is None:
            raise RecursoNoEncontrado("el género", genero_id)
        pagina = await uow.generos.listar_libros(genero_id, params)

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
