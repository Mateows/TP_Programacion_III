"""Dependencias de autenticación y autorización por roles.

``get_current_user`` carga la cuenta desde la base en cada petición: el token
identifica, nunca autoriza. Los permisos salen de ``asignacion_rol`` (RN-04) y
los roles del claim ``roles`` quedan como información de lo que se emitió al
iniciar sesión.

Son dos consultas por petición autenticada (cuenta y roles). Se acepta el
costo porque una revocación debe tener efecto inmediato, sin esperar a que
venza el token (design, decisión 4).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import (
    JWTPayload,
    decode_access_token,
    token_emitido_antes_del_cambio,
)
from app.modules.auth.repository import AsignacionRolRepository, UsuarioRepository
from app.modules.usuarios.models import Usuario

# Mensajes de la capa HTTP: genéricos, sin detalles de esquema ni de la cuenta
# (RN-18). El cliente distingue 401 de 403, no el motivo exacto del rechazo.
MENSAJE_SIN_SESION = "No hay sesión activa"
MENSAJE_SESION_INVALIDA = "Sesión inválida o vencida"
MENSAJE_CAMBIO_PENDIENTE = "Debe cambiar su contraseña antes de continuar"
MENSAJE_SIN_PERMISOS = "No tiene permisos para este recurso"


def ahora_utc() -> datetime:
    """Reloj de la aplicación usado para resolver la vigencia de los roles."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Cuenta autenticada con sus roles vigentes y los del token.

    ``roles_vigentes`` son los que autorizan y salen de la base en cada
    petición; ``roles_token`` son informativos y reflejan lo emitido al
    iniciar sesión.
    """

    usuario: Usuario
    roles_vigentes: list[str]
    roles_token: list[str]

    @property
    def id(self) -> int | None:
        """Clave primaria de la cuenta autenticada."""
        return self.usuario.id

    @property
    def debe_cambiar_password(self) -> bool:
        """Estado del cambio obligatorio según la cuenta cargada de la base."""
        return self.usuario.debe_cambiar_password

    def tiene_rol(self, rol: str) -> bool:
        """Indica si el rol está vigente en la base, no si viajó en el token."""
        return rol in self.roles_vigentes


def _no_autorizado(detalle: str) -> HTTPException:
    """Construye el 401 de sesión ausente o inválida."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
    )


def _id_de(payload: JWTPayload) -> int | None:
    """Extrae el ``sub`` numérico del token, o ``None`` si no lo es."""
    sub = payload.get("sub")
    if isinstance(sub, bool) or not isinstance(sub, (int, str)):
        return None

    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def roles_del_token(payload: JWTPayload) -> list[str]:
    """Devuelve el claim ``roles`` como lista de textos (solo informativo)."""
    roles = payload.get("roles", [])
    if not isinstance(roles, list):
        return []

    return [rol for rol in roles if isinstance(rol, str)]


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> UsuarioAutenticado:
    """Resuelve la cuenta autenticada a partir de la cookie ``access_token``.

    Orden del diseño: sin cookie → 401; token inválido o vencido → 401; ``sub``
    sin cuenta → 401; cuenta inactiva → 401; token emitido antes del último
    cambio de contraseña → 401; y recién entonces se consultan los roles
    vigentes.
    """
    if access_token is None:
        raise _no_autorizado(MENSAJE_SIN_SESION)

    payload = decode_access_token(access_token)
    if payload is None:
        raise _no_autorizado(MENSAJE_SESION_INVALIDA)

    usuario_id = _id_de(payload)
    if usuario_id is None:
        raise _no_autorizado(MENSAJE_SESION_INVALIDA)

    usuario = await UsuarioRepository(session).get(usuario_id)
    if usuario is None or not usuario.activo:
        raise _no_autorizado(MENSAJE_SESION_INVALIDA)

    if token_emitido_antes_del_cambio(payload, usuario.password_cambiada_en):
        raise _no_autorizado(MENSAJE_SESION_INVALIDA)

    asignaciones = await AsignacionRolRepository(session).listar_vigentes(
        usuario_id,
        ahora_utc(),
    )

    return UsuarioAutenticado(
        usuario=usuario,
        roles_vigentes=[asignacion.rol for asignacion in asignaciones],
        roles_token=roles_del_token(payload),
    )


CurrentUser = Annotated[UsuarioAutenticado, Depends(get_current_user)]
RoleChecker = Callable[[UsuarioAutenticado], Awaitable[UsuarioAutenticado]]


async def require_password_change(current_user: CurrentUser) -> None:
    """Rechaza con 403 si la cuenta tiene el cambio de contraseña pendiente.

    El estado se lee de la cuenta cargada en la base, no del claim del token:
    un cambio resuelto o forzado en la base manda sobre lo que diga el token.
    """
    if current_user.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MENSAJE_CAMBIO_PENDIENTE,
        )


def requiere_rol(*roles_requeridos: str) -> RoleChecker:
    """Dependencia que exige al menos uno de los roles vigentes indicados.

    Los roles se evalúan contra ``asignacion_rol`` en cada petición: un rol
    revocado deja de autorizar de inmediato y uno otorgado se reconoce sin
    emitir un token nuevo (RN-04).
    """

    async def role_checker(current_user: CurrentUser) -> UsuarioAutenticado:
        if not any(current_user.tiene_rol(rol) for rol in roles_requeridos):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=MENSAJE_SIN_PERMISOS,
            )

        return current_user

    return role_checker
