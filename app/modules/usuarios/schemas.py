"""Contratos de entrada y salida del módulo de usuarios.

Los contratos de entrada usan ``extra="forbid"``: un campo que el contrato no
declara es un error de validación, no un dato ignorado. El catálogo de roles
asignables desde la API excluye ``CLIENTE``: ese rol nace con el auto-registro,
que además crea la ficha de cliente (RN-02).

La contraseña provisoria reutiliza el límite de 1 a 72 bytes UTF-8 del módulo
de autenticación para que las dos reglas no diverjan.

``PaginaResponse`` se reexporta desde ``app.core.paginacion``: el envoltorio es
el mismo para todos los listados y ningún módulo debe importar de ``usuarios``
para paginar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.paginacion import PaginaResponse
from app.modules.auth.schemas import PasswordValidadaMixin

# Roles que un administrador puede otorgar desde la API. ``CLIENTE`` queda
# fuera a propósito: su ficha la crea el auto-registro (RN-02).
ROLES_ASIGNABLES: tuple[str, ...] = ("ADMIN", "RECEPCION", "MECANICO")

RolAsignable = Literal["ADMIN", "RECEPCION", "MECANICO"]


class AltaUsuarioRequest(PasswordValidadaMixin, BaseModel):
    """Datos del alta de una cuenta de personal, con contraseña provisoria."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=255)
    nombre: str = Field(max_length=150)
    password: str


class AsignacionRolRequest(BaseModel):
    """Rol a otorgar y su vencimiento opcional.

    ``desde`` y ``otorgada_por`` no se aceptan en el cuerpo: los fija el
    servicio con el reloj de la aplicación y la cuenta actuante, para que la
    auditoría de la asignación no se pueda falsear.
    """

    model_config = ConfigDict(extra="forbid")

    rol: RolAsignable
    vence_en: datetime | None = None

    @field_validator("vence_en")
    @classmethod
    def _validar_vence_en(cls, valor: datetime | None) -> datetime | None:
        """Exige un vencimiento futuro y con zona horaria."""
        if valor is None:
            return None
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError("El vencimiento debe incluir zona horaria")
        if valor <= datetime.now(UTC):
            raise ValueError("El vencimiento debe ser posterior al momento actual")
        return valor


class UsuarioCreadoResponse(BaseModel):
    """Cuenta de personal recién creada, sin credenciales ni roles."""

    model_config = ConfigDict(extra="forbid")

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool


class AsignacionRolResponse(BaseModel):
    """Asignación de rol con su vigencia y su revocación."""

    model_config = ConfigDict(extra="forbid")

    id: int
    rol: str
    desde: datetime
    vence_en: datetime | None
    revocada_en: datetime | None
    otorgada_por: int | None


class EventoSeguridadResponse(BaseModel):
    """Evento de seguridad del historial auditable."""

    model_config = ConfigDict(extra="forbid")

    id: int
    cuando: datetime
    actor: str
    accion: str

