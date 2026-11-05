"""Lógica del módulo ventas.

Reglas duras que este módulo implementa:

- **RN-09**: la venta nace con sus renglones (al menos uno, sin libros
  repetidos), con el precio de cada renglón **copiado del libro** y el total
  **calculado por el servidor**. Las ventas no se modifican: no hay PATCH.
- **RN-10**: registrar una venta descuenta el stock de cada libro y deja un
  movimiento por renglón. Si un libro no alcanza, no queda ninguna de esas
  escrituras: ni la venta, ni los renglones, ni los descuentos, ni los
  movimientos. Eso lo garantiza **un solo Unit of Work**: las cuatro clases de
  escritura (venta, renglones, stock y movimientos) viven en la misma
  transacción.
- **RN-13**: un libro dado de baja no se puede vender (409).
- **RN-14**: lo propio sólo pide estar autenticado: un cliente ve sus ventas y
  ninguna otra.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from fastapi import HTTPException

from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.paginacion import Page, PageParams
from app.modules.libros.service import MOTIVO_VENTA, aplicar_movimiento_stock
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import VentaCreate
from app.modules.ventas.unit_of_work import VentasUnitOfWork

_MSJ_CONFLICTO = (
    "No se pudo registrar la venta: cliente o libro inexistente, "
    "libro dado de baja o stock insuficiente."
)

ROLES_PERSONAL = ("ADMIN", "VENDEDOR")


async def registrar(
    uow: VentasUnitOfWork,
    data: VentaCreate,
    *,
    usuario_id: int,
) -> Venta:
    """Registra la venta con sus renglones, el descuento de stock y los movimientos.

    Todo en **un solo bloque**: si un libro no alcanza, no queda ninguna
    escritura (ni venta, ni renglones, ni descuentos, ni movimientos).
    """
    try:
        async with uow:
            cliente = await uow.clientes.get_by_id(data.cliente_id)
            if cliente is None:
                raise Conflicto(
                    "No se pudo registrar la venta: el cliente no existe."
                )

            libros = await uow.libros.obtener_varios_including_deleted(
                [r.libro_id for r in data.renglones]
            )
            if len(libros) != len(data.renglones):
                raise Conflicto(
                    "No se pudo registrar la venta: algún libro no existe."
                )

            # Comprobaciones antes de escribir: si alguna falla, el bloque
            # revierte y no queda nada a medias.
            for renglon in data.renglones:
                libro = libros[renglon.libro_id]
                if libro.borrado_en is not None:
                    raise Conflicto(
                        "No se pudo registrar la venta: el libro "
                        f"'{libro.titulo}' está dado de baja."
                    )
                if libro.stock < renglon.cantidad:
                    raise Conflicto(
                        "No se pudo registrar la venta: no alcanza el stock de "
                        f"'{libro.titulo}'."
                    )

            # El precio se copia del libro y el total lo calcula el servidor.
            total = sum(
                libros[r.libro_id].precio * r.cantidad for r in data.renglones
            )
            venta = Venta(cliente_id=data.cliente_id, total=total)
            await uow.ventas.add(venta)  # flush: ya tenemos venta.id

            for renglon in data.renglones:
                libro = libros[renglon.libro_id]
                await uow.renglones.add(
                    RenglonVenta(
                        venta_id=venta.id,
                        libro_id=libro.id,
                        cantidad=renglon.cantidad,
                        precio_unitario=libro.precio,
                    )
                )
                # Descuento del stock: pasa por el único punto de escritura.
                await aplicar_movimiento_stock(
                    uow,
                    libro,
                    -renglon.cantidad,
                    MOTIVO_VENTA,
                    usuario_id,
                    venta_id=venta.id,
                )
    except IntegrityError:
        raise Conflicto(_MSJ_CONFLICTO) from None

    return venta


async def listar(uow: VentasUnitOfWork, params: PageParams) -> Page[Venta]:
    """Listado paginado de ventas (sólo el personal)."""
    async with uow:
        return await uow.ventas.listar(params)


async def obtener_detalle(
    uow: VentasUnitOfWork,
    venta_id: int,
    *,
    usuario_id: int,
) -> Venta:
    """Detalle de una venta.

    El personal (ADMIN o VENDEDOR) puede ver cualquier venta. Un cliente ve
    **sólo las suyas**: la comprobación de dueño devuelve 403 si la venta es de
    otro (RN-14).
    """
    async with uow:
        venta = await uow.ventas.get_detalle(venta_id)
        if venta is None:
            raise RecursoNoEncontrado("la venta", venta_id)

        roles_vigentes = await uow.roles.roles_vigentes(usuario_id)
        if not set(roles_vigentes) & set(ROLES_PERSONAL):
            # Es un cliente: la venta tiene que ser suya.
            cliente = await uow.clientes.get_by_usuario(usuario_id)
            if cliente is None or venta.cliente_id != cliente.id:
                raise HTTPException(
                    status_code=403,
                    detail="No tenés permiso para ver esta venta.",
                )
    return venta


async def mis_ventas(
    uow: VentasUnitOfWork, usuario_id: int, params: PageParams
) -> Page:
    """Ventas del cliente de la sesión (RN-14).

    Un usuario del personal no tiene ficha de cliente: su lista es vacía.
    """
    async with uow:
        cliente = await uow.clientes.get_by_usuario(usuario_id)
        if cliente is None:
            return Page.create(items=[], total=0, params=params)
        pagina = await uow.ventas.listar_de_cliente(cliente.id, params)

    return Page.create(
        items=[
            {"id": v.id, "fecha": v.fecha, "total": v.total} for v in pagina.items
        ],
        total=pagina.total,
        params=params,
    )
