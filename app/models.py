"""Registro central de los modelos del dominio.

Alembic (``migrations/env.py``) importa **este módulo** para que el metadata
conozca todas las tablas y las relaciones se resuelvan entre módulos.

Los modelos se reparten por módulo funcional (``app/modules/<módulo>/models.py``)
para que cada módulo sea dueño de sus tablas, pero las relaciones cruzan
módulos: por eso las anotaciones se declaran como cadenas y sólo se importan
bajo ``TYPE_CHECKING``. Sin este punto único, importar un solo módulo dejaría
las relaciones sin resolver.
"""

from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)
from app.modules.ventas.models import RenglonVenta, Venta

__all__ = [
    "AsignacionRol",
    "Autor",
    "Cliente",
    "Editorial",
    "EventoSeguridad",
    "Genero",
    "IntentoAcceso",
    "Libro",
    "LibroAutor",
    "MovimientoStock",
    "PerfilCliente",
    "RenglonVenta",
    "Usuario",
    "Venta",
]
