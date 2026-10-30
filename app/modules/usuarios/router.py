"""Rutas HTTP de administración de usuarios, roles y eventos.

El router no conoce reglas de negocio: traduce los errores de dominio del
servicio a ``404``, ``409`` y ``422`` y devuelve los contratos de salida. El
``401`` y el ``403`` los resuelven las dependencias: primero la sesión, después
el cambio obligatorio de contraseña (dependencia de grupo) y por último el rol
``ADMIN`` (dependencia por ruta).

Se montan en ``router_protegido`` con prefijos ``/usuarios`` y ``/eventos``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioAutenticado, requiere_rol
from app.core.paginacion import ParametrosPagina
from app.core.repository import ConflictoDeIntegridad
from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.errors import (
    AsignacionNoEncontrada,
    CorreoYaRegistrado,
    PaginaFueraDeRango,
    PasswordInvalida,
    RevocacionPropiaNoPermitida,
    RolNoAsignable,
    RolYaAsignado,
    UltimoAdministrador,
    UsuarioNoEncontrado,
    VencimientoInvalido,
)
from app.modules.usuarios.schemas import (
    AltaUsuarioRequest,
    AsignacionRolRequest,
    AsignacionRolResponse,
    EventoSeguridadResponse,
    PaginaResponse,
    RolAsignable,
    UsuarioCreadoResponse,
)
from app.modules.usuarios.service import (
    asignar_rol,
    consultar_eventos,
    consultar_roles,
    crear_usuario_personal,
    revocar_rol,
)

router_usuarios = APIRouter(tags=["usuarios"])
router_eventos = APIRouter(tags=["eventos"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[UsuarioAutenticado, Depends(requiere_rol("ADMIN"))]

# Todos los errores de dominio del módulo, para no repetir la tupla en cada
# ruta. La traducción a estado vive en ``_traducir``.
ERRORES_DE_USUARIOS = (
    UsuarioNoEncontrado,
    AsignacionNoEncontrada,
    CorreoYaRegistrado,
    RolYaAsignado,
    RevocacionPropiaNoPermitida,
    UltimoAdministrador,
    RolNoAsignable,
    VencimientoInvalido,
    PaginaFueraDeRango,
    PasswordInvalida,
    ConflictoDeIntegridad,
)


def _traducir(error: Exception) -> HTTPException:
    """Traduce un error de dominio al estado HTTP que le corresponde.

    El mensaje es el del error de dominio, que nunca incluye nombres de tablas,
    columnas ni restricciones (RN-18).
    """
    if isinstance(error, (UsuarioNoEncontrado, AsignacionNoEncontrada)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    if isinstance(
        error,
        (
            CorreoYaRegistrado,
            RolYaAsignado,
            RevocacionPropiaNoPermitida,
            UltimoAdministrador,
            ConflictoDeIntegridad,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(error),
    )


@router_usuarios.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UsuarioCreadoResponse,
)
async def alta_de_personal(
    datos: AltaUsuarioRequest,
    actor: AdminDep,
    session: SessionDep,
) -> UsuarioCreadoResponse:
    """Crea una cuenta de personal sin roles y con cambio de contraseña pendiente."""
    try:
        return await crear_usuario_personal(UnitOfWork(session), datos, actor.usuario)
    except ERRORES_DE_USUARIOS as error:
        raise _traducir(error) from error


@router_usuarios.get(
    "/{usuario_id}/roles",
    response_model=list[AsignacionRolResponse],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)
async def historial_de_roles(
    usuario_id: int,
    session: SessionDep,
) -> list[AsignacionRolResponse]:
    """Devuelve todas las asignaciones de rol de la cuenta, abiertas o no."""
    try:
        return await consultar_roles(UnitOfWork(session), usuario_id)
    except ERRORES_DE_USUARIOS as error:
        raise _traducir(error) from error


@router_usuarios.post(
    "/{usuario_id}/roles",
    status_code=status.HTTP_201_CREATED,
    response_model=AsignacionRolResponse,
)
async def alta_de_rol(
    usuario_id: int,
    datos: AsignacionRolRequest,
    actor: AdminDep,
    session: SessionDep,
) -> AsignacionRolResponse:
    """Otorga un rol a una cuenta existente, con vencimiento opcional."""
    try:
        return await asignar_rol(
            UnitOfWork(session),
            usuario_id,
            datos,
            actor.usuario,
        )
    except ERRORES_DE_USUARIOS as error:
        raise _traducir(error) from error


@router_usuarios.delete(
    "/{usuario_id}/roles/{rol}",
    response_model=AsignacionRolResponse,
)
async def baja_de_rol(
    usuario_id: int,
    rol: RolAsignable,
    actor: AdminDep,
    session: SessionDep,
) -> AsignacionRolResponse:
    """Revoca la asignación abierta de un rol, sin borrar la fila.

    ``rol`` se valida contra el catálogo asignable en el propio path: el mismo
    ``422`` que la asignación, sin llegar al servicio. ``CLIENTE`` queda
    reservado al auto-registro (RN-02).
    """
    try:
        return await revocar_rol(
            UnitOfWork(session),
            usuario_id,
            rol,
            actor.usuario,
        )
    except ERRORES_DE_USUARIOS as error:
        raise _traducir(error) from error


@router_eventos.get(
    "",
    response_model=PaginaResponse[EventoSeguridadResponse],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)
async def historial_de_eventos(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaResponse[EventoSeguridadResponse]:
    """Devuelve los eventos de seguridad paginados, del más reciente al más viejo."""
    parametros = ParametrosPagina(page=page, size=size)
    try:
        return await consultar_eventos(UnitOfWork(session), parametros)
    except ERRORES_DE_USUARIOS as error:
        raise _traducir(error) from error
