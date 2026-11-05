"""Servicios del módulo de acceso.

Reglas duras que este módulo implementa:

- **El hash se calcula antes de abrir la transacción**: adentro, la conexión
  quedaría tomada los ~300 ms que tarda bcrypt sin usar la base.
- **El límite de intentos se evalúa PRIMERO** (RN-07): si hay 5 fallos con el
  mismo ``(email, ip)`` en 60 s, se responde 429 con ``Retry-After`` **sin
  calcular ni verificar ningún hash**.
- **Mismo cuerpo y duración exista o no el correo** (RN-08): cuando el correo
  no existe se verifica contra el **hash ficticio** calculado una vez en el
  lifespan.
- **Cada intento se anota en su propia sesión y transacción, confirmada
  siempre** (Ejercicio 7): es la única escritura del sistema que no comparte
  la transacción de su petición.
- El **auto-registro** (RN-02) crea el usuario, su rol CLIENTE y su ficha de
  cliente en **un solo bloque**: o quedan las tres filas, o ninguna.
- Los **eventos de seguridad** (RN-16) comparten la transacción del cambio que
  los provoked: o quedan los dos, o ninguno.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.paginacion import Page, PageParams
from app.core.security import crear_token, hash_password, verify_password
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)
from app.modules.usuarios.repository import IntentoAccesoRepository
from app.modules.usuarios.schemas import (
    CambioPassword,
    LoginCrear,
    RegistroCrear,
    RolAsignar,
    UsuarioCrear,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

# Literales a propósito: el nombre del status cambió entre versiones de Starlette.
HTTP_401 = 401
HTTP_404 = 404
HTTP_429 = 429

VENTANA_INTENTOS = timedelta(seconds=60)
MAXIMO_FALLOS = 5

MENSAJE_CREDENCIALES = "Credenciales inválidas."
MENSAJE_PASSWORD_ACTUAL = "La contraseña actual no es correcta."
MENSAJE_AUTOPROTECCION = (
    "Un administrador no puede revocarse su propio rol ADMIN."
)
MENSAJE_ULTIMO_ADMIN = "El sistema no puede quedar sin administradores vigentes."
MENSAJE_ROL_NO_ASIGNADO = (
    "El usuario no tiene una asignación abierta con ese rol."
)

ACTOR_SISTEMA = "SISTEMA"


def actor_de(usuario: Usuario) -> str:
    """Texto del actor para ``evento_seguridad``/``otorgada_por``.

    El correo identifica al usuario de forma legible; se recorta a 120 porque
    así lo declara la columna (un correo larguísimo no debe terminar en un 422
    de datos al auditar). ``'SISTEMA'`` es otro actor posible y no es un
    usuario.
    """
    return usuario.email[:120]


async def registrar(uow: UsuariosUnitOfWork, datos: RegistroCrear) -> Usuario:
    """Auto-registro: usuario + rol CLIENTE + ficha de cliente (RN-02).

    Las tres filas viven en **un solo UoW**: o quedan las tres, o ninguna. El
    correo repetido choca contra los UNIQUE de la base (``usuario.email`` y
    ``cliente.email``) y el handler central lo traduce a 409. No hay consulta
    previa de unicidad ni se apropia de una ficha existente: si ya existe un
    cliente con ese correo, el registro da 409.
    """
    # bcrypt ANTES de abrir la transacción.
    password_hash = await hash_password(datos.password)
    ahora = datetime.now(timezone.utc)

    usuario = Usuario(
        email=datos.email,
        nombre=datos.nombre,
        password_hash=password_hash,
        activo=True,
        # El auto-registro no es una clave provisoria: el cliente eligió su
        # propia contraseña, así que no queda obligado a cambiarla.
        debe_cambiar_password=False,
    )

    async with uow:
        await uow.usuarios.add(usuario)  # flush: ya tenemos usuario.id

        await uow.roles.add(
            AsignacionRol(
                usuario_id=usuario.id,
                rol="CLIENTE",
                desde=ahora,
                otorgada_por="AUTOREGISTRO",
            )
        )
        await uow.clientes.add(
            Cliente(
                usuario_id=usuario.id,
                nombre=datos.nombre,
                email=datos.email,
            )
        )
        await uow.eventos.add(
            EventoSeguridad(
                cuando=ahora,
                actor=ACTOR_SISTEMA,
                accion=f"Auto-registro del cliente id {usuario.id}",
            )
        )

    return usuario


async def crear_personal(
    uow: UsuariosUnitOfWork,
    datos: UsuarioCrear,
    *,
    actor: str,
) -> Usuario:
    """Crea el usuario con contraseña provisoria (``POST /usuarios``, ADMIN).

    ``debe_cambiar_password=True`` es la clave provisoria que le da el admin:
    hasta que la cambie, el grupo protegido le responde 403 (RN-06). El alta y
    su evento de seguridad comparten el mismo UoW (RN-16).
    """
    password_hash = await hash_password(datos.password)
    ahora = datetime.now(timezone.utc)

    usuario = Usuario(
        email=datos.email,
        nombre=datos.nombre,
        password_hash=password_hash,
        activo=True,
        debe_cambiar_password=True,
    )

    async with uow:
        await uow.usuarios.add(usuario)
        await uow.eventos.add(
            EventoSeguridad(
                cuando=ahora,
                actor=actor,
                accion=f"Alta de usuario id {usuario.id}",
            )
        )

    return usuario


async def autenticar(
    uow: UsuariosUnitOfWork,
    session_maker: async_sessionmaker[AsyncSession],
    datos: LoginCrear,
    *,
    ip: str,
    hash_ficticio: str,
) -> tuple[Usuario, list[str], str]:
    """Login completo: límite de intentos → verificación → intento → token.

    Devuelve el usuario, sus roles vigentes y el JWT. El router pone el token en
    la cookie; el cuerpo de la respuesta no lo lleva.
    """
    ahora = datetime.now(timezone.utc)

    # 1. PRIMERO el límite de intentos (RN-07). Cuesta una consulta y, si ya
    #    se superó, evita cualquier cálculo de hash.
    async with uow:
        segundos = await _segundos_para_reintentar(uow, datos.email, ip, ahora)
        if segundos is not None:
            raise HTTPException(
                status_code=HTTP_429,
                detail=(
                    "Demasiados intentos fallidos. "
                    f"Intentá de nuevo en {segundos} segundos."
                ),
                headers={"Retry-After": str(segundos)},
            )

        # 2. Recién ahora se busca el usuario y sus roles vigentes.
        usuario = await uow.usuarios.get_by_email(datos.email)
        roles = await uow.roles.roles_vigentes(usuario.id, ahora) if usuario else []

    # 3. La verificación corre FUERA de la transacción (bcrypt ~300 ms). Si el
    #    correo no existe se usa el hash ficticio del lifespan: misma respuesta
    #    y duración parecida (RN-08).
    hash_a_verificar = usuario.password_hash if usuario is not None else hash_ficticio
    credencial_valida = await verify_password(datos.password, hash_a_verificar)

    # Un usuario inactivo no inicia sesión. La contraseña se verifica igual para
    # no distinguir por tiempo entre «no existe», «inactivo» y «clave mala».
    if usuario is not None and not usuario.activo:
        credencial_valida = False

    # 4. El intento se anota SIEMPRE, en su propia sesión y transacción.
    await _anotar_intento(session_maker, datos.email, ip, credencial_valida)

    if not credencial_valida or usuario is None:
        raise HTTPException(status_code=HTTP_401, detail=MENSAJE_CREDENCIALES)

    # 5. Token con los roles VIGENTES al emitirlo. Son informativos: la
    #    autorización real se consulta en la base en cada petición (RN-04).
    token = crear_token(sub=str(usuario.id), roles=roles)
    return usuario, roles, token


async def _segundos_para_reintentar(
    uow: UsuariosUnitOfWork,
    email: str,
    ip: str,
    ahora: datetime,
) -> int | None:
    """``Retry-After`` si ya hay 5 fallos vigentes; ``None`` si se puede intentar.

    La ventana es de 60 s y se reinicia con el último login correcto de ese
    ``(email, ip)``: los fallos anteriores siguen en la tabla pero dejan de
    contar (RN-07). El ``Retry-After`` es el tiempo que falta para que el fallo
    más antiguo salga de la ventana.
    """
    ventana_inicio = ahora - VENTANA_INTENTOS
    ultimo_exito = await uow.intentos.ultimo_exito(email, ip)

    desde = ventana_inicio
    despues_de: datetime | None = None
    if ultimo_exito is not None and ultimo_exito > ventana_inicio:
        desde = ultimo_exito
        despues_de = ultimo_exito

    total, mas_antiguo = await uow.intentos.contar_fallos(
        email, ip, desde=desde, despues_de=despues_de
    )
    if total < MAXIMO_FALLOS:
        return None

    referencia = mas_antiguo or ahora
    faltan = (referencia + VENTANA_INTENTOS - ahora).total_seconds()
    return max(1, math.ceil(faltan))


async def _anotar_intento(
    session_maker: async_sessionmaker[AsyncSession],
    email: str,
    ip: str,
    exito: bool,
) -> None:
    """Anota el intento en una sesión y transacción **propias** (Ejercicio 7).

    Tres cosas que este código deja written a propósito:

    1. **Qué hace distinto**: abre una sesión nueva desde la fábrica del
       lifespan y confirma su propia transacción; no usa la de la petición.
    2. **Por qué no puede compartir la transacción**: el fallo que se quiere
       contar es justamente el que revierte la transacción de la petición. Si
       compartieran la sesión, el ``rollback`` del login fallido borraría
       justamente el intento que hay que contar.
    3. **Cuál es su costo**: deja filas aunque la petición falle. Es el costo
       aceptado de que el registro de intentos sobreviva al rollback.
    """
    async with session_maker() as sesion:
        async with UnitOfWork(sesion):
            await IntentoAccesoRepository(sesion, IntentoAcceso).add(
                IntentoAcceso(
                    cuando=datetime.now(timezone.utc),
                    email=email,
                    ip=ip,
                    exito=exito,
                )
            )


async def roles_vigentes(uow: UsuariosUnitOfWork, usuario_id: int) -> list[str]:
    """Roles vigentes consultados en la base (para ``GET /auth/yo``)."""
    async with uow:
        return await uow.roles.roles_vigentes(usuario_id)


async def listar_roles(
    uow: UsuariosUnitOfWork, usuario_id: int
) -> list[AsignacionRol]:
    """Historial completo de roles del usuario (``GET /usuarios/{id}/roles``).

    Incluye filas revocadas y vencidas: revocar no borra. 404 si el usuario no
    existe.
    """
    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise RecursoNoEncontrado("el usuario", usuario_id)
        return await uow.roles.listar_por_usuario(usuario_id)


async def asignar_rol(
    uow: UsuariosUnitOfWork,
    usuario_id: int,
    datos: RolAsignar,
    *,
    actor: str,
) -> AsignacionRol:
    """Asigna un rol con vigencia opcional (``POST /usuarios/{id}/roles``).

    Reglas (RN-03):

    - Una asignación **abierta repetida** responde 409 porque la base tiene el
      índice único parcial ``(usuario_id, rol) WHERE revocada_en IS NULL``. No
      se consulta antes para rechazarla: si la fila abierta sigue vigente se
      intenta el insert y la base decide.
    - Una fila abierta **vencida** ocupa el índice (sólo mira ``revocada_en``):
      se cierra escribiendo ``revocada_en`` y recién después se abre la nueva.
    - ``vence_en`` ya llegó con zona horaria y en el futuro (422 si no).
    """
    ahora = datetime.now(timezone.utc)

    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise RecursoNoEncontrado("el usuario", usuario_id)

        abierta = await uow.roles.get_abierta(usuario_id, datos.rol)
        if (
            abierta is not None
            and abierta.vence_en is not None
            and abierta.vence_en <= ahora
        ):
            # Cerrar la vencida libera el índice parcial; el historial queda.
            abierta.revocada_en = ahora
            await uow.roles.update(abierta)

        nueva = AsignacionRol(
            usuario_id=usuario_id,
            rol=datos.rol,
            desde=datos.desde or ahora,
            vence_en=datos.vence_en,
            otorgada_por=actor,
        )
        # Si la abierta seguía vigente, este flush choca con el índice parcial
        # y el handler central lo traduce a 409 con mensaje propio.
        await uow.roles.add(nueva)
        await uow.eventos.add(
            EventoSeguridad(
                cuando=ahora,
                actor=actor,
                accion=f"Asignación de rol {datos.rol} al usuario id {usuario_id}",
            )
        )

    return nueva


async def revocar_rol(
    uow: UsuariosUnitOfWork,
    usuario_id: int,
    rol: str,
    *,
    admin: Usuario,
) -> AsignacionRol:
    """Revoca un rol escribiendo ``revocada_en``; la fila no se borra.

    Autoprotección (RN-05) → **409**:

    - un administrador no puede revocarse su propio rol ADMIN;
    - el sistema nunca queda con 0 ADMINs vigentes.

    El efecto es inmediato: la siguiente petición de la sesión afectada
    consulta ``asignacion_rol`` y recibe 403, sin esperar a que venza el token
    (RN-04, caso C-07).
    """
    ahora = datetime.now(timezone.utc)

    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise RecursoNoEncontrado("el usuario", usuario_id)

        abierta = await uow.roles.get_abierta(usuario_id, rol)
        if abierta is None:
            raise HTTPException(
                status_code=HTTP_404, detail=MENSAJE_ROL_NO_ASIGNADO
            )

        if rol == "ADMIN":
            if usuario_id == admin.id:
                raise Conflicto(MENSAJE_AUTOPROTECCION)
            vigentes = await uow.roles.contar_vigentes("ADMIN", ahora)
            if vigentes <= 1:
                raise Conflicto(MENSAJE_ULTIMO_ADMIN)

        abierta.revocada_en = ahora
        await uow.roles.update(abierta)
        await uow.eventos.add(
            EventoSeguridad(
                cuando=ahora,
                actor=actor_de(admin),
                accion=f"Revocación de rol {rol} al usuario id {usuario_id}",
            )
        )

    return abierta


async def listar_eventos(
    uow: UsuariosUnitOfWork, params: PageParams
) -> Page[EventoSeguridad]:
    """Página de ``evento_seguridad`` para ``GET /eventos`` (sólo ADMIN)."""
    async with uow:
        return await uow.eventos.list_page(params)


async def cambiar_password(
    uow: UsuariosUnitOfWork,
    usuario: Usuario,
    datos: CambioPassword,
) -> None:
    """Cambia la contraseña del usuario.

    Es un login tradicional con cookie: cambiar la contraseña **no invalida las
    sesiones abiertas ni emite un token nuevo**. La sesión sigue hasta que el
    token vence o se cierra.

    La contraseña actual se verifica con bcrypt; si no coincide, 401. El hash
    nuevo se calcula **antes** de abrir la transacción del cambio. El evento de
    seguridad comparte el UoW del cambio (RN-16): o quedan los dos, o ninguno.
    """
    actual_valida = await verify_password(datos.password_actual, usuario.password_hash)
    if not actual_valida:
        raise HTTPException(status_code=HTTP_401, detail=MENSAJE_PASSWORD_ACTUAL)

    nuevo_hash = await hash_password(datos.password_nueva)
    cambiada_en = datetime.now(timezone.utc)

    async with uow:
        usuario.password_hash = nuevo_hash
        usuario.debe_cambiar_password = False
        await uow.usuarios.update(usuario)
        await uow.eventos.add(
            EventoSeguridad(
                cuando=cambiada_en,
                actor=actor_de(usuario),
                accion="Cambio de contraseña",
            )
        )
