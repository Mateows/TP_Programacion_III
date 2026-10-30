"""Modelos de tabla del módulo de usuarios.

Cuentas de acceso, asignaciones de rol con vigencia y revocación, intentos
de acceso y eventos de seguridad. Los roles no son una columna de
``usuario``: son filas de ``asignacion_rol`` vigentes.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Index, func, text
from sqlmodel import Field, SQLModel

# Catálogo cerrado de roles admitidos (RN-02). El servicio lo reutiliza.
ROLES_VALIDOS: tuple[str, ...] = ("ADMIN", "RECEPCION", "MECANICO", "CLIENTE")


class Usuario(SQLModel, table=True):
    """Cuenta de acceso del taller con credenciales propias."""

    __tablename__ = "usuario"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True)
    nombre: str = Field(max_length=150)
    password_hash: str = Field(max_length=255)
    activo: bool = Field(default=True, nullable=False)
    debe_cambiar_password: bool = Field(default=False, nullable=False)
    password_cambiada_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class AsignacionRol(SQLModel, table=True):
    """Rol otorgado a un usuario, con vigencia y revocación opcionales.

    La regla "a lo sumo una asignación abierta por rol" (RN-03) la sostiene
    la base: índice único parcial sobre ``(usuario_id, rol)`` limitado a las
    filas sin revocar.
    """

    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('ADMIN', 'RECEPCION', 'MECANICO', 'CLIENTE')",
            name="ck_asignacion_rol_rol",
        ),
        Index(
            "ix_asignacion_rol_usuario_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True, nullable=False)
    rol: str = Field(max_length=20, nullable=False)
    desde: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
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
    otorgada_por: int | None = Field(
        default=None,
        foreign_key="usuario.id",
        index=True,
        nullable=True,
    )


class IntentoAcceso(SQLModel, table=True):
    """Intento de acceso, exitoso o fallido, para el conteo de RN-08.

    No referencia ``usuario.id``: un intento puede corresponder a un correo
    inexistente y el registro debe sobrevivir a cualquier cambio de cuenta.
    """

    __tablename__ = "intento_acceso"
    __table_args__ = (
        Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    email: str = Field(max_length=255, nullable=False)
    ip: str = Field(max_length=45, nullable=False)
    exito: bool = Field(nullable=False)


class EventoSeguridad(SQLModel, table=True):
    """Evento auditable; el actor es texto y puede ser ``SISTEMA``.

    Sin clave foránea a ``usuario``: el evento debe sobrevivir a la baja o
    al cambio de la cuenta que lo originó.
    """

    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    actor: str = Field(max_length=100, nullable=False)
    accion: str = Field(max_length=255, nullable=False)
