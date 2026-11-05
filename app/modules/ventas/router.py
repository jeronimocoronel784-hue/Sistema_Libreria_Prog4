"""Rutas del módulo ventas.

Todas van en el grupo **protegido**: exigen sesión y el control de cambio
obligatorio. El registro de ventas es del personal (VENDEDOR o ADMIN) y la
consulta de una venta la puede hacer el personal o el cliente dueño (RN-14).
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActual, get_usuario_actual, requiere_rol
from app.core.paginacion import Page, PageParamsDep
from app.modules.ventas import service
from app.modules.ventas.models import Venta
from app.modules.ventas.schemas import VentaCreate, VentaEnLista, VentaRead
from app.modules.ventas.unit_of_work import VentasUnitOfWork

# El registro de uvicorn: con un logger propio sin configurar, el aviso NO
# aparecería ni en la consola ni en `docker logs` (requisito del parcial).
logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/ventas", tags=["ventas"])
propios_router = APIRouter(prefix="/mis-ventas", tags=["ventas"])


def get_ventas_uow(
    session: AsyncSession = Depends(get_session),
) -> VentasUnitOfWork:
    """Construye el Unit of Work de ventas con la sesión de la petición."""
    return VentasUnitOfWork(session)


async def _avisar_comprobante(venta_id: int, email: str | None) -> None:
    """Aviso simulado al cliente: corre en segundo plano tras la respuesta.

    Se agenda con ``BackgroundTasks`` y corre **después** de enviar la
    respuesta, y sólo si la operación se confirmó.
    """
    await asyncio.sleep(0.5)
    logger.info(
        "Comprobante de la venta %s enviado a %s", venta_id, email or "cliente"
    )


def _detalle(venta: Venta) -> dict:
    """Arma el detalle de la venta.

    El diccionario se arma a mano (y no con ``model_dump``) porque las
    relaciones son bidireccionales: ``venta.cliente.ventas`` volvería a la
    venta y el volcado sería recursivo.
    """
    return {
        "id": venta.id,
        "fecha": venta.fecha,
        "total": venta.total,
        "cliente": (
            {
                "id": venta.cliente.id,
                "nombre": venta.cliente.nombre,
                "email": venta.cliente.email,
            }
            if venta.cliente is not None
            else None
        ),
        "renglones": [
            {
                "libro_id": r.libro_id,
                "titulo": r.libro.titulo if r.libro is not None else None,
                "cantidad": r.cantidad,
                "precio_unitario": r.precio_unitario,
                "subtotal": r.precio_unitario * r.cantidad,
            }
            for r in sorted(venta.renglones, key=lambda x: x.id or 0)
        ],
    }


@router.post("/", response_model=VentaRead, status_code=201)
async def crear_venta(
    data: VentaCreate,
    background_tasks: BackgroundTasks,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
) -> dict:
    """Registra una venta con sus renglones.

    201 con los precios copiados y el total calculado por el servidor; 409 si
    el cliente o el libro no existen, si el libro está dado de baja o si no
    alcanza el stock (en ese caso no queda ninguna escritura); 422 si el cuerpo
    no cumple el contrato.
    """
    venta = await service.registrar(uow, data, usuario_id=personal.usuario.id)
    detalle = await service.obtener_detalle(
        uow, venta.id, usuario_id=personal.usuario.id
    )
    cliente = detalle.cliente
    background_tasks.add_task(
        _avisar_comprobante, venta.id, cliente.email if cliente else None
    )
    return _detalle(detalle)


@router.get("/", response_model=Page[VentaEnLista])
async def listar_ventas(
    params: PageParamsDep,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
) -> dict:
    """Listado paginado de ventas. 200; 422 si el paging no cumple el contrato."""
    pagina = await service.listar(uow, params)
    return pagina.model_dump()


@propios_router.get("/")
async def mis_ventas(
    params: PageParamsDep,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
) -> dict:
    """Ventas del cliente de la sesión (sólo pide estar autenticado).

    200; 422 si el paging no cumple el contrato. Un usuario del personal no
    tiene ficha de cliente: su lista es vacía.
    """
    pagina = await service.mis_ventas(uow, actual.usuario.id, params)
    return pagina.model_dump()


@router.get("/{venta_id}", response_model=VentaRead)
async def obtener_venta(
    venta_id: int,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
) -> dict:
    """Detalle de una venta.

    200 para el personal y para el cliente dueño; 403 si es la venta de otro
    cliente; 404 si la venta no existe.
    """
    venta = await service.obtener_detalle(
        uow, venta_id, usuario_id=actual.usuario.id
    )
    return _detalle(venta)
