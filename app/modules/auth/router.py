"""Rutas HTTP del módulo de autenticación.

El token viaja únicamente en la cookie ``access_token``: ningún cuerpo de
respuesta lo incluye. Los errores de dominio del servicio se traducen acá a
``401``, ``409``, ``422`` y ``429``, siempre con mensajes genéricos (RN-18).

Este router se monta en ``router_abierto`` con dependencias por ruta:
``/auth/yo`` y ``/auth/cambiar-password`` exigen sesión, pero no pasan por
``router_protegido``, que aplica el cambio obligatorio de contraseña a nivel de
grupo y devolvería ``403`` justo a quien necesita cambiar la contraseña
(RN-06).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionFactory, get_session, get_session_factory
from app.core.dependencies import CurrentUser
from app.core.repository import ConflictoDeIntegridad
from app.core.unit_of_work import UnitOfWork
from app.modules.auth.cookies import borrar_cookie_sesion, fijar_cookie_sesion
from app.modules.auth.errors import (
    CorreoYaRegistrado,
    CredencialesInvalidas,
    LimiteDeIntentosExcedido,
    PasswordInvalida,
)
from app.modules.auth.schemas import (
    CambioPasswordRequest,
    LoginRequest,
    MensajeResponse,
    MensajeSesionResponse,
    RegistroRequest,
    SesionResponse,
)
from app.modules.auth.service import (
    SesionEmitida,
    cambiar_password,
    consultar_sesion,
    iniciar_sesion,
    registrar_cuenta,
)
from app.modules.clientes.errors import DocumentoYaRegistrado

router = APIRouter(tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionFactoryDep = Annotated[SessionFactory, Depends(get_session_factory)]


def _mensaje(resultado: SesionEmitida, mensaje: str) -> MensajeSesionResponse:
    """Arma la respuesta de sesión sin exponer el token."""
    return MensajeSesionResponse(
        mensaje=mensaje,
        debe_cambiar_password=resultado.debe_cambiar_password,
        expira_en_segundos=resultado.expira_en_segundos,
    )


def _ip_de(request: Request) -> str:
    """Dirección de origen del intento, o ``desconocida`` si el ASGI no la da."""
    return request.client.host if request.client is not None else "desconocida"


@router.post(
    "/registro",
    status_code=status.HTTP_201_CREATED,
    response_model=MensajeSesionResponse,
)
async def registro(
    datos: RegistroRequest,
    response: Response,
    session: SessionDep,
) -> MensajeSesionResponse:
    """Crea la cuenta de cliente, su ficha, y deja la sesión iniciada."""
    try:
        resultado = await registrar_cuenta(UnitOfWork(session), datos)
    except (
        CorreoYaRegistrado,
        DocumentoYaRegistrado,
        ConflictoDeIntegridad,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    fijar_cookie_sesion(response, resultado.token)
    return _mensaje(resultado, "Cuenta creada")


@router.post("/login", response_model=MensajeSesionResponse)
async def login(
    datos: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    session_factory: SessionFactoryDep,
) -> MensajeSesionResponse:
    """Autentica la cuenta y entrega la cookie de sesión."""
    try:
        resultado = await iniciar_sesion(
            UnitOfWork(session),
            session_factory,
            datos,
            _ip_de(request),
        )
    except CredencialesInvalidas as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
    except LimiteDeIntentosExcedido as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
            headers={"Retry-After": str(error.retry_after)},
        ) from error

    fijar_cookie_sesion(response, resultado.token)
    return _mensaje(resultado, "Sesión iniciada")


@router.post("/logout", response_model=MensajeResponse)
async def logout(response: Response) -> MensajeResponse:
    """Cierra la sesión borrando la cookie, haya o no sesión válida."""
    borrar_cookie_sesion(response)
    return MensajeResponse(mensaje="Sesión cerrada")


@router.get("/yo", response_model=SesionResponse)
async def yo(current_user: CurrentUser, session: SessionDep) -> SesionResponse:
    """Devuelve la cuenta autenticada con sus roles vigentes e informativos."""
    return await consultar_sesion(
        UnitOfWork(session),
        current_user.usuario,
        current_user.roles_token,
    )


@router.post("/cambiar-password", response_model=MensajeSesionResponse)
async def cambiar_password_propia(
    datos: CambioPasswordRequest,
    response: Response,
    current_user: CurrentUser,
    session: SessionDep,
) -> MensajeSesionResponse:
    """Cambia la contraseña de la cuenta autenticada y renueva la sesión."""
    try:
        resultado = await cambiar_password(
            UnitOfWork(session),
            current_user.usuario,
            datos,
        )
    except CredencialesInvalidas as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
    except PasswordInvalida as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    fijar_cookie_sesion(response, resultado.token)
    return _mensaje(resultado, "Contraseña actualizada")
