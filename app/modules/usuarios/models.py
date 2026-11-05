"""Modelos del módulo de acceso: Usuario, AsignacionRol, IntentoAcceso y EventoSeguridad.

Los nombres de tablas y columnas son obligatorios (consigna, sección "Modelo de
dominio"). Las reglas que viven en la base y no en el código:

- ``usuario.email`` es UNIQUE.
- ``asignacion_rol.rol`` tiene CHECK contra los tres roles del sistema.
- ``asignacion_rol`` tiene un índice único **parcial** ``(usuario_id, rol)``
  ``WHERE revocada_en IS NULL``: a lo sumo una asignación abierta por rol
  (RN-03). Revocar escribe ``revocada_en``; la fila no se borra nunca.
- ``intento_acceso`` lleva el índice ``(email, ip, cuando)`` que alimenta el
  límite de intentos de login (RN-07).
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import MovimientoStock

# Los tres roles que el administrador asigna y revoca (RN-03/RN-04).
ROLES = ("ADMIN", "VENDEDOR", "CLIENTE")
ROLES_VALIDOS = "rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')"


def _ahora() -> datetime:
    """Marca de tiempo con zona horaria (todas las fechas del esquema son timestamptz)."""
    return datetime.now(timezone.utc)


class Usuario(SQLModel, table=True):
    """Cuenta de acceso. El rol **no** es una columna: vive en ``asignacion_rol``."""

    __tablename__ = "usuario"
    __table_args__ = (UniqueConstraint("email", name="uq_usuario_email"),)

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column(String(320), nullable=False))
    nombre: str = Field(sa_column=Column(String(120), nullable=False))
    password_hash: str = Field(sa_column=Column(String(255), nullable=False))
    activo: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("true")),
    )
    debe_cambiar_password: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )

    # Navegación declarada en los dos extremos. `uselist=False`: un cliente
    # tiene, o no, acceso por la web (Cliente.usuario_id es UNIQUE).
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"uselist": False},
    )
    asignaciones_rol: list["AsignacionRol"] = Relationship(back_populates="usuario")
    movimientos_stock: list["MovimientoStock"] = Relationship(
        back_populates="usuario"
    )


class AsignacionRol(SQLModel, table=True):
    """Rol otorgado a un usuario, con vigencia e historial (RN-03, RN-05).

    Los roles de una persona son las filas **vigentes**: no revocadas
    (``revocada_en IS NULL``) y sin vencer (``vence_en IS NULL`` o futuro).
    """

    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint(ROLES_VALIDOS, name="ck_asignacion_rol_rol_valido"),
        Index("ix_asignacion_rol_usuario_id", "usuario_id"),
        Index(
            "uq_asignacion_rol_usuario_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", name="fk_asignacion_rol_usuario", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    rol: str = Field(sa_column=Column(String(20), nullable=False))
    desde: datetime = Field(
        default_factory=_ahora,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )
    vence_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    revocada_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # Texto y no FK: el rol puede otorgarlo el SISTEMA, que no es un usuario
    # (mismo criterio que `evento_seguridad.actor`).
    otorgada_por: str | None = Field(
        default=None,
        sa_column=Column(String(120), nullable=True),
    )

    usuario: "Usuario" = Relationship(
        back_populates="asignaciones_rol",
        sa_relationship_kwargs={"foreign_keys": "AsignacionRol.usuario_id"},
    )


class IntentoAcceso(SQLModel, table=True):
    """Cada intento de login, correcto o fallido (RN-07).

    Se anota desde una sesión y una transacción propias que se confirman
    siempre: es la única escritura del sistema que no comparte la transacción
    de su petición (el fallo que se quiere contar es el mismo que la revierte).
    """

    __tablename__ = "intento_acceso"
    __table_args__ = (
        Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        default_factory=_ahora,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )
    email: str = Field(sa_column=Column(String(320), nullable=False))
    ip: str = Field(sa_column=Column(String(45), nullable=False))
    exito: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))


class EventoSeguridad(SQLModel, table=True):
    """Auditoría de altas de personal, cambios de rol y de contraseña (RN-16).

    ``actor`` es texto a propósito: ``'SISTEMA'`` no es un usuario.
    """

    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        default_factory=_ahora,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )
    actor: str = Field(sa_column=Column(String(120), nullable=False))
    accion: str = Field(sa_column=Column(String(200), nullable=False))
