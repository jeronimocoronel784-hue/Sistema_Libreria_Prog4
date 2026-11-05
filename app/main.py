"""Aplicación FastAPI, lifespan y los dos grupos de rutas.

- **Grupo abierto**: ``/health``, ``/auth`` y el catálogo. El catálogo es
  público y ``/auth`` tiene que poder usarse para iniciarla.
- **Grupo protegido**: todo lo demás. Lleva el control del cambio obligatorio de
  contraseña montado **una sola vez**: FastAPI suma dependencias y no las
  resta, así que el control tiene que ir a nivel de grupo y no de ruta.

``/auth/yo`` y ``/auth/cambiar-password`` están en el grupo abierto pero
exigen sesión por dentro (``get_usuario_actual``): si estuvieran en el grupo
protegido, un usuario con contraseña provisoria no podría cambiar la clave
nunca (RN-06).
"""

import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI

from app.core.database import close_engine, init_engine_and_session
from app.core.dependencies import exigir_password_al_dia
from app.core.errors import registrar_manejadores
from app.core.security import hash_password
from app.modules.autores.router import router as autores_router
from app.modules.autores.router import router_admin as autores_admin_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.editoriales.router import router_admin as editoriales_admin_router
from app.modules.generos.router import router as generos_router
from app.modules.generos.router import router_admin as generos_admin_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.libros.router import router_admin as libros_admin_router
from app.modules.usuarios.auth_router import router as auth_router
from app.modules.usuarios.router import eventos_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.ventas.router import propios_router as ventas_propias_router
from app.modules.ventas.router import router as ventas_router

# Registro central de modelos: sin este import, las relaciones que cruzan
# módulos no se resuelven. Se importa el registro y no un módulo suelto.
import app.models  # noqa: F401  # isort: skip


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación.

    El motor y la fábrica de sesiones se crean **acá**, nunca al importar un
    módulo: un recurso construido al importar se crea antes de que exista el
    bucle de eventos.
    """
    engine, session_factory = init_engine_and_session()
    app.state.engine = engine
    app.state.session_factory = session_factory

    # Hash ficticio del login: se calcula **UNA vez**, con el coste de la
    # configuración. Cuando el correo no existe, el login verifica contra este
    # hash para responder igual y tardar parecido, sin revelar qué cuentas hay
    # (RN-08).
    app.state.hash_ficticio = await hash_password(secrets.token_urlsafe(32))

    try:
        yield
    finally:
        await close_engine(engine)


def create_app() -> FastAPI:
    app = FastAPI(title="Librería de barrio", lifespan=lifespan)

    # Traducción central de errores: IntegrityError -> 409, validación -> 422.
    # Se registra antes de montar los routers para que cubra todos los
    # endpoints.
    registrar_manejadores(app)

    # --- Dos grupos de rutas (RN-06) ---------------------------------------
    # El control de ``debe_cambiar_password`` se monta **una sola vez**, como
    # dependencia del grupo protegido. El grupo abierto no lo lleva.
    grupo_abierto = APIRouter()
    grupo_protegido = APIRouter(dependencies=[Depends(exigir_password_al_dia)])

    # Abierto: salud, autenticación y catálogo público.
    grupo_abierto.include_router(health_router)
    grupo_abierto.include_router(auth_router)
    grupo_abierto.include_router(editoriales_router)
    grupo_abierto.include_router(generos_router)
    grupo_abierto.include_router(autores_router)
    grupo_abierto.include_router(libros_router)

    # Protegido: personal, roles, auditoría, escrituras del catálogo, clientes
    # y ventas. El 401 lo aporta ``get_usuario_actual``, el 403 del cambio
    # pendiente el grupo, y el permiso por rol ``requiere_rol`` en cada ruta,
    # consultando la base en cada petición (RN-04).
    grupo_protegido.include_router(usuarios_router)
    grupo_protegido.include_router(eventos_router)
    grupo_protegido.include_router(editoriales_admin_router)
    grupo_protegido.include_router(generos_admin_router)
    grupo_protegido.include_router(autores_admin_router)
    grupo_protegido.include_router(libros_admin_router)
    grupo_protegido.include_router(clientes_router)
    grupo_protegido.include_router(ventas_router)
    grupo_protegido.include_router(ventas_propias_router)

    app.include_router(grupo_abierto)
    app.include_router(grupo_protegido)
    return app


app = create_app()
