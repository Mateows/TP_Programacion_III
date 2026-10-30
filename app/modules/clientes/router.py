"""Rutas HTTP de clientes y vehículos.

El router no conoce reglas de negocio: recibe la sesión y la cuenta actuante,
delega en ``service.py`` y traduce los errores de dominio a ``403``, ``404``,
``409`` y ``422``. El ``401`` y el ``403`` por cambio de contraseña los resuelve
``router_protegido``; el ``403`` por rol, la dependencia de cada ruta.

Tres routers porque las rutas no comparten prefijo: ``router_clientes`` se monta
con ``/clientes``, ``router_vehiculos`` con ``/vehiculos`` y
``router_mis_vehiculos`` sin prefijo, para que ``/mis-vehiculos`` no cuelgue de
``/vehiculos``. ``/mis-vehiculos`` usa ``CurrentUser`` y no ``requiere_rol``
(RN-17): el dueño de la consulta es la propia cuenta.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import CurrentUser, UsuarioAutenticado, requiere_rol
from app.core.repository import ConflictoDeIntegridad
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.errors import (
    AnioFueraDeRango,
    ClienteNoEncontrado,
    DocumentoYaRegistrado,
    PatenteYaRegistrada,
    SinFichaDeCliente,
    VehiculoConOrdenesAbiertas,
    VehiculoNoEncontrado,
)
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.clientes.schemas import (
    AltaClienteRequest,
    AltaVehiculoRequest,
    ClienteConVehiculosResponse,
    ClienteResponse,
    VehiculoResponse,
)
from app.modules.clientes.service import (
    ClienteConVehiculos,
    consultar_cliente,
    crear_cliente,
    crear_vehiculo,
    dar_de_baja_vehiculo,
    listar_mis_vehiculos,
)
from app.modules.ordenes.verificacion import VerificadorOrdenesAbiertasSQL

router_clientes = APIRouter(tags=["clientes"])
router_vehiculos = APIRouter(tags=["vehiculos"])
router_mis_vehiculos = APIRouter(tags=["clientes"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PersonalDep = Annotated[
    UsuarioAutenticado,
    Depends(requiere_rol("RECEPCION", "ADMIN")),
]

# Todos los errores de dominio del módulo, para no repetir la tupla en cada
# ruta. La traducción a estado vive en ``_traducir``.
ERRORES_DE_CLIENTES = (
    ClienteNoEncontrado,
    DocumentoYaRegistrado,
    VehiculoNoEncontrado,
    PatenteYaRegistrada,
    VehiculoConOrdenesAbiertas,
    SinFichaDeCliente,
    AnioFueraDeRango,
    ConflictoDeIntegridad,
)


def _traducir(error: Exception) -> HTTPException:
    """Traduce un error de dominio al estado HTTP que le corresponde.

    El mensaje es el del error de dominio, que nunca incluye nombres de tablas,
    columnas ni restricciones (RN-18). ``SinFichaDeCliente`` es un ``403`` y no
    un ``404``: la cuenta existe, lo que falta es su ficha del taller.
    """
    if isinstance(error, (ClienteNoEncontrado, VehiculoNoEncontrado)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    if isinstance(
        error,
        (
            DocumentoYaRegistrado,
            PatenteYaRegistrada,
            VehiculoConOrdenesAbiertas,
            ConflictoDeIntegridad,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    if isinstance(error, SinFichaDeCliente):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(error),
    )


def _ficha(cliente: Cliente) -> ClienteResponse:
    """Convierte la entidad de tabla al contrato de salida de la ficha."""
    return ClienteResponse.model_validate(cliente, from_attributes=True)


def _vehiculo(vehiculo: Vehiculo) -> VehiculoResponse:
    """Convierte la entidad de tabla al contrato de salida del vehículo."""
    return VehiculoResponse.model_validate(vehiculo, from_attributes=True)


@router_clientes.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ClienteResponse,
)
async def alta_de_cliente(
    datos: AltaClienteRequest,
    actor: PersonalDep,
    session: SessionDep,
) -> ClienteResponse:
    """Da de alta una ficha de cliente del taller (personal del taller)."""
    try:
        cliente = await crear_cliente(UnitOfWork(session), datos, actor.usuario)
    except ERRORES_DE_CLIENTES as error:
        raise _traducir(error) from error

    return _ficha(cliente)


@router_clientes.get(
    "/{cliente_id}",
    response_model=ClienteConVehiculosResponse,
)
async def consulta_de_cliente(
    cliente_id: int,
    actor: PersonalDep,
    session: SessionDep,
) -> ClienteConVehiculosResponse:
    """Devuelve la ficha de un cliente con sus vehículos vigentes."""
    del actor  # Autoriza la dependencia; la consulta no usa la cuenta actuante.
    try:
        ficha: ClienteConVehiculos = await consultar_cliente(
            UnitOfWork(session),
            cliente_id,
        )
    except ERRORES_DE_CLIENTES as error:
        raise _traducir(error) from error

    return ClienteConVehiculosResponse(
        **_ficha(ficha.cliente).model_dump(),
        vehiculos=[_vehiculo(vehiculo) for vehiculo in ficha.vehiculos],
    )


@router_clientes.post(
    "/{cliente_id}/vehiculos",
    status_code=status.HTTP_201_CREATED,
    response_model=VehiculoResponse,
)
async def alta_de_vehiculo(
    cliente_id: int,
    datos: AltaVehiculoRequest,
    actor: PersonalDep,
    session: SessionDep,
) -> VehiculoResponse:
    """Registra un vehículo para un cliente existente (personal del taller)."""
    try:
        vehiculo = await crear_vehiculo(
            UnitOfWork(session),
            cliente_id,
            datos,
            actor.usuario,
        )
    except ERRORES_DE_CLIENTES as error:
        raise _traducir(error) from error

    return _vehiculo(vehiculo)


@router_vehiculos.delete(
    "/{vehiculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def baja_de_vehiculo(
    vehiculo_id: int,
    actor: PersonalDep,
    session: SessionDep,
) -> None:
    """Da de baja lógica un vehículo vigente sin órdenes abiertas.

    ``Response`` como clase de retorno deja el cuerpo vacío: el ``204`` no
    lleva entidad. La fila se conserva con su marca de baja.
    """
    try:
        await dar_de_baja_vehiculo(
            UnitOfWork(session),
            vehiculo_id,
            actor.usuario,
            VerificadorOrdenesAbiertasSQL(session),
        )
    except ERRORES_DE_CLIENTES as error:
        raise _traducir(error) from error


@router_mis_vehiculos.get(
    "/mis-vehiculos",
    response_model=list[VehiculoResponse],
)
async def mis_vehiculos(
    current_user: CurrentUser,
    session: SessionDep,
) -> list[VehiculoResponse]:
    """Lista los vehículos vigentes de la ficha de la cuenta autenticada.

    La ficha se resuelve por la cuenta de la sesión, nunca por un id del
    llamador. Sin ficha de cliente la respuesta es ``403``.
    """
    # ``get_current_user`` carga la cuenta desde la base: siempre tiene clave.
    usuario_id = cast(int, current_user.id)
    try:
        vehiculos = await listar_mis_vehiculos(
            UnitOfWork(session),
            usuario_id,
        )
    except ERRORES_DE_CLIENTES as error:
        raise _traducir(error) from error

    return [_vehiculo(vehiculo) for vehiculo in vehiculos]
