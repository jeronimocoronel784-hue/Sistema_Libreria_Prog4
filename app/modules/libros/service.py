"""Lógica del módulo libros.

Reglas duras que este módulo implementa:

- **El stock tiene una sola vía de escritura** (RN-11): ``aplicar_movimiento_stock``
  es el **único** punto del sistema donde se escribe ``libro.stock``, y lo hace
  siempre junto a un movimiento. Lo usan el alta con stock inicial, la
  reposición y el registro de ventas.
- **El borrado es lógico** (RN-13): ``dar_de_baja`` anota ``borrado_en`` y no
  borra la fila, porque las ventas viejas la siguen apuntando.
- El ISBN es único **entre los vigentes**: lo garantiza el índice único parcial
  de la base, no una consulta previa.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.paginacion import Page, PageParams
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.repository import (
    LibroRepository,
    MovimientoStockRepository,
)
from app.modules.libros.schemas import LibroCreate, LibroUpdate
from app.modules.libros.unit_of_work import LibrosUnitOfWork

_MSJ_CONFLICTO_LIBRO = (
    "No se pudo guardar el libro: el ISBN ya está en uso entre los vigentes, "
    "o la editorial, el género o el autor no existen."
)
_MSJ_LIBRO_DADO_DE_BAJA = "El libro está dado de baja: no se puede reponer."

MOTIVO_STOCK_INICIAL = "Stock inicial"
MOTIVO_REPOSICION = "Reposición"
MOTIVO_VENTA = "Venta"


class StockUnitOfWork(Protocol):
    """Lo que hace falta del Unit of Work para escribir stock.

    Lo satisfacen ``LibrosUnitOfWork`` y ``VentasUnitOfWork``: los dos
    tienen el repositorio de libros y el de movimientos.
    """

    libros: LibroRepository
    movimientos: MovimientoStockRepository


async def aplicar_movimiento_stock(
    uow: StockUnitOfWork,
    libro: Libro,
    cantidad: int,
    motivo: str,
    usuario_id: int,
    *,
    venta_id: int | None = None,
) -> MovimientoStock:
    """**Único punto de escritura del stock** (RN-11).

    Suma el movimiento al stock del libro y deja la fila en
    ``movimiento_stock``. ``cantidad`` es con signo: positiva entra, negativa
    sale. El stock de un libro es siempre la suma de sus movimientos.

    Lo usan las tres operaciones que mueven stock: el alta con stock inicial,
    la reposición y el registro de ventas.
    """
    libro.stock += cantidad
    await uow.libros.update(libro)
    return await uow.movimientos.add(
        MovimientoStock(
            libro_id=libro.id,
            venta_id=venta_id,
            usuario_id=usuario_id,
            cantidad=cantidad,
            motivo=motivo,
        )
    )


async def crear(
    uow: LibrosUnitOfWork,
    data: LibroCreate,
    *,
    usuario_id: int,
) -> Libro:
    """Alta de libro con stock inicial y sus autores, en una sola transacción.

    El stock inicial no se escribe directo en el libro: entra como un
    movimiento (RN-11). Sin ``if`` previos: la base valida las FK y el ISBN
    único entre los vigentes, y el error se traduce a 409.
    """
    libro = Libro(
        isbn=data.isbn,
        titulo=data.titulo,
        precio=data.precio,
        stock=0,
        editorial_id=data.editorial_id,
        genero_id=data.genero_id,
    )

    try:
        async with uow:
            await uow.libros.add(libro)  # flush: ya tenemos libro.id
            for autoria in data.autores:
                await uow.autorias.agregar(
                    libro.id, autoria.autor_id, autoria.rol, autoria.orden
                )
            if data.stock_inicial > 0:
                await aplicar_movimiento_stock(
                    uow,
                    libro,
                    data.stock_inicial,
                    MOTIVO_STOCK_INICIAL,
                    usuario_id,
                )
    except IntegrityError:
        raise Conflicto(_MSJ_CONFLICTO_LIBRO) from None

    return libro


async def listar(
    uow: LibrosUnitOfWork,
    params: PageParams,
    titulo: str | None = None,
    genero_id: int | None = None,
) -> Page[Libro]:
    """Listado paginado del catálogo (sólo los vigentes)."""
    async with uow:
        return await uow.libros.listar(params, titulo=titulo, genero_id=genero_id)


async def obtener_detalle(uow: LibrosUnitOfWork, libro_id: int) -> Libro:
    """Detalle con editorial, género y autores, en un número fijo de consultas."""
    async with uow:
        libro = await uow.libros.get_detalle(libro_id)
    if libro is None:
        raise RecursoNoEncontrado("el libro", libro_id)
    return libro


async def actualizar(
    uow: LibrosUnitOfWork, libro_id: int, data: LibroUpdate
) -> Libro:
    """PATCH parcial: sólo título y precio. El stock no se edita (RN-11)."""
    async with uow:
        libro = await uow.libros.get_detalle(libro_id)
        if libro is None:
            raise RecursoNoEncontrado("el libro", libro_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(libro, campo, valor)
        try:
            await uow.libros.update(libro)
        except IntegrityError:
            raise Conflicto(_MSJ_CONFLICTO_LIBRO) from None
    return libro


async def dar_de_baja(uow: LibrosUnitOfWork, libro_id: int) -> None:
    """Borrado lógico: anota ``borrado_en`` y conserva la fila (RN-13).

    La fila sigue existiendo porque las ventas viejas la apuntan y tienen que
    seguir mostrando el título. El ISBN queda libre para volver a cargarlo.
    """
    async with uow:
        libro = await uow.libros.soft_delete(libro_id)
        if libro is None:
            raise RecursoNoEncontrado("el libro", libro_id)


async def reponer(
    uow: LibrosUnitOfWork,
    libro_id: int,
    cantidad: int,
    *,
    usuario_id: int,
) -> Libro:
    """Reposición de stock: el stock sube y queda un movimiento (RN-11).

    Un libro dado de baja no se puede reponer (RN-13): 409.
    """
    async with uow:
        libro = await uow.libros.get_by_id_including_deleted(libro_id)
        if libro is None:
            raise RecursoNoEncontrado("el libro", libro_id)
        if libro.borrado_en is not None:
            raise Conflicto(_MSJ_LIBRO_DADO_DE_BAJA)
        await aplicar_movimiento_stock(
            uow, libro, cantidad, MOTIVO_REPOSICION, usuario_id
        )
    return libro


async def movimientos(
    uow: LibrosUnitOfWork, libro_id: int, params: PageParams
) -> Page[MovimientoStock]:
    """Movimientos de stock de un libro, paginados (sólo ADMIN)."""
    async with uow:
        libro = await uow.libros.get_by_id_including_deleted(libro_id)
        if libro is None:
            raise RecursoNoEncontrado("el libro", libro_id)
        return await uow.movimientos.listar_por_libro(libro_id, params)
