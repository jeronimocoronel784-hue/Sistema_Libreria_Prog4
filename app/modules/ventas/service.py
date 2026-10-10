"""Lógica del módulo ventas (incluye RenglonVenta por composición)."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import VentaCreate

_MSJ_CONFLICTO = (
    "No se pudo registrar la venta: cliente o libro inexistente, "
    "o datos inválidos."
)


async def crear(session: AsyncSession, data: VentaCreate) -> dict:
    """Crea la venta con sus renglones.

    El precio se copia del libro y el total lo calcula el servidor.
    La existencia del cliente la valida la base (FK -> 409).
    """
    res = await session.execute(
        select(Libro).where(
            Libro.id.in_([r.libro_id for r in data.renglones])
        )
    )
    precios = {libro.id: libro.precio for libro in res.scalars().all()}
    faltantes = [r.libro_id for r in data.renglones if r.libro_id not in precios]
    if faltantes:
        raise HTTPException(
            status_code=409,
            detail="No se pudo registrar la venta: libro inexistente.",
        )
    total = sum(precios[r.libro_id] * r.cantidad for r in data.renglones)
    venta = Venta(cliente_id=data.cliente_id, total=total)
    session.add(venta)
    try:
        await session.flush()
        for renglon in data.renglones:
            session.add(
                RenglonVenta(
                    venta_id=venta.id,
                    libro_id=renglon.libro_id,
                    cantidad=renglon.cantidad,
                    precio_unitario=precios[renglon.libro_id],
                )
            )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    return await obtener_detalle(session, venta.id)


async def listar(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Venta]:
    # sin relaciones en respuesta: el listado no precarga a propósito.
    res = await session.execute(
        select(Venta).order_by(Venta.id).offset(offset).limit(limit)
    )
    return list(res.scalars().all())


async def obtener_detalle(session: AsyncSession, venta_id: int) -> dict:
    """Detalle con cliente y renglones en un número fijo de consultas."""
    res = await session.execute(
        select(Venta)
        .where(Venta.id == venta_id)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
    )
    venta = res.scalars().first()
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada.")
    renglones = []
    for r in sorted(venta.renglones, key=lambda x: x.id or 0):
        subtotal = r.precio_unitario * r.cantidad
        renglones.append(
            {
                "libro_id": r.libro_id,
                "titulo": r.libro.titulo if r.libro is not None else None,
                "cantidad": r.cantidad,
                "precio_unitario": r.precio_unitario,
                "subtotal": subtotal,
            }
        )
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
        "renglones": renglones,
    }
