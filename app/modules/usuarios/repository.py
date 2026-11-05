"""Repositorios del módulo de acceso.

- ``UsuarioRepository``: alta y consulta de cuentas.
- ``AsignacionRolRepository``: roles vigentes, historial y asignaciones abiertas.
- ``IntentoAccesoRepository``: conteo de intentos para el límite del login.
- ``EventoSeguridadRepository``: historial de auditoría (sólo agregado).
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlmodel import select

from app.core.repository import BaseRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)


class UsuarioRepository(BaseRepository[Usuario]):
    """Acceso a la tabla ``usuario``."""

    _orden_por = (Usuario.id,)

    async def get_by_email(self, email: str) -> Usuario | None:
        """Usuario por correo (el correo es UNIQUE en la base)."""
        statement = select(Usuario).where(Usuario.email == email)
        return (await self.session.exec(statement)).first()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    """Acceso a la tabla ``asignacion_rol``.

    Un rol **vigente** es una fila no revocada (``revocada_en IS NULL``) y sin
    vencer (``vence_en IS NULL`` o futuro). La autorización se decide con estos
    roles, consultados en la base en cada petición (RN-04).
    """

    _orden_por = (AsignacionRol.id,)

    async def roles_vigentes(
        self, usuario_id: int, ahora: datetime | None = None
    ) -> list[str]:
        """Roles vigentes del usuario, ordenados."""
        momento = ahora or datetime.now(timezone.utc)
        statement = (
            select(AsignacionRol.rol)
            .where(
                AsignacionRol.usuario_id == usuario_id,
                AsignacionRol.revocada_en.is_(None),
                (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > momento),
            )
            .order_by(AsignacionRol.rol)
        )
        return list((await self.session.exec(statement)).all())

    async def get_abierta(self, usuario_id: int, rol: str) -> AsignacionRol | None:
        """Asignación abierta (no revocada) de ese rol, vigente o vencida."""
        statement = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None),
        )
        return (await self.session.exec(statement)).first()

    async def listar_por_usuario(self, usuario_id: int) -> list[AsignacionRol]:
        """Historial completo de roles del usuario (incluye revocados y vencidos)."""
        statement = (
            select(AsignacionRol)
            .where(AsignacionRol.usuario_id == usuario_id)
            .order_by(AsignacionRol.id)
        )
        return list((await self.session.exec(statement)).all())

    async def contar_vigentes(self, rol: str, ahora: datetime | None = None) -> int:
        """Cuántos usuarios tienen ese rol vigente ahora."""
        momento = ahora or datetime.now(timezone.utc)
        statement = select(func.count()).select_from(AsignacionRol).where(
            AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None),
            (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > momento),
        )
        return int((await self.session.execute(statement)).scalar_one())


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    """Acceso a la tabla ``intento_acceso`` (el límite del login la consulta)."""

    _orden_por = (IntentoAcceso.id,)

    async def ultimo_exito(self, email: str, ip: str) -> datetime | None:
        """Cuándo fue el último login correcto de ese ``(email, ip)``.

        Un login correcto reinicia la cuenta: los fallos anteriores siguen en
        la tabla, pero dejan de contar (RN-07).
        """
        statement = (
            select(IntentoAcceso.cuando)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .order_by(IntentoAcceso.cuando.desc())
            .limit(1)
        )
        return (await self.session.exec(statement)).first()

    async def contar_fallos(
        self,
        email: str,
        ip: str,
        desde: datetime,
        despues_de: datetime | None = None,
    ) -> tuple[int, datetime | None]:
        """Cuántos intentos fallidos hubo y cuándo fue el más antiguo.

        Devuelve ``(total, mas_antiguo)``: el más antiguo es el que define el
        ``Retry-After``.
        """
        condiciones = [
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
            IntentoAcceso.cuando >= desde,
        ]
        if despues_de is not None:
            condiciones.append(IntentoAcceso.cuando > despues_de)

        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(IntentoAcceso)
                .where(*condiciones)
            )
            or 0
        )
        if total == 0:
            return 0, None

        mas_antiguo = await self.session.scalar(
            select(func.min(IntentoAcceso.cuando)).where(*condiciones)
        )
        return total, mas_antiguo


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    """Acceso a la tabla ``evento_seguridad``: sólo se agregan líneas."""
