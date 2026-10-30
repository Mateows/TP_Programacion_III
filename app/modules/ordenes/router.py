"""Rutas HTTP del módulo de órdenes de trabajo.

El router no conoce reglas de negocio: recibe la sesión y la cuenta actuante,
delega en ``service.py`` y traduce los errores de dominio a ``403``, ``404``,
``409`` y ``422``. El ``401`` y el ``403`` por cambio de contraseña los resuelve
``router_protegido``; el ``403`` por rol, la dependencia de cada ruta.

El alta y el listado son de personal del taller. El detalle exige sesión
(``CurrentUser``) y la regla de personal o dueño vive en el servicio.
``/estados-orden`` es un catálogo de sólo lectura abierto a cualquier cuenta
autenticada.

Las transiciones ``iniciar``, ``terminar`` y ``cancelar`` responden el detalle
actualizado. Iniciar exige ``MECANICO`` por dependencia; terminar exige
``ADMIN`` o ``MECANICO`` y el servicio distingue al mecánico asignado; cancelar
sólo exige sesión porque el dueño del vehículo también puede. El aviso
simulado de la terminación se agenda con ``BackgroundTasks`` después de que la
unidad de trabajo confirmó.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import CurrentUser, UsuarioAutenticado, requiere_rol
from app.core.paginacion import PaginaFueraDeRango, PaginaResponse, ParametrosPagina
from app.core.unit_of_work import UnitOfWork
from app.modules.ordenes.avisos import avisar_terminacion
from app.modules.ordenes.errors import (
    CatalogoDeEstadosVacio,
    EstadoNoDeclarado,
    OrdenNoEncontrada,
    RepuestoNoDisponible,
    SinPermisoSobreLaOrden,
    StockInsuficiente,
    TransicionNoPermitida,
    VehiculoNoDisponible,
)
from app.modules.clientes.errors import SinFichaDeCliente
from app.modules.ordenes.schemas import (
    AltaOrdenRequest,
    EstadoOrdenResponse,
    OrdenDetalleResponse,
    OrdenResumenResponse,
)
from app.modules.ordenes.service import (
    cancelar_orden,
    consultar_orden,
    crear_orden,
    iniciar_orden,
    listar_estados,
    listar_mis_ordenes,
    listar_ordenes,
    terminar_orden,
)

router_ordenes = APIRouter(tags=["ordenes"])
router_mis_ordenes = APIRouter(tags=["ordenes"])
router_estados_orden = APIRouter(tags=["estados-orden"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AltaDep = Annotated[
    UsuarioAutenticado,
    Depends(requiere_rol("ADMIN", "RECEPCION")),
]
PersonalDep = Annotated[
    UsuarioAutenticado,
    Depends(requiere_rol("ADMIN", "RECEPCION", "MECANICO")),
]
MecanicoDep = Annotated[
    UsuarioAutenticado,
    Depends(requiere_rol("MECANICO")),
]
TerminarDep = Annotated[
    UsuarioAutenticado,
    Depends(requiere_rol("ADMIN", "MECANICO")),
]

# Todos los errores de dominio del módulo, para no repetir la tupla en cada
# ruta. La traducción a estado vive en ``_traducir``.
ERRORES_DE_ORDENES = (
    CatalogoDeEstadosVacio,
    VehiculoNoDisponible,
    RepuestoNoDisponible,
    TransicionNoPermitida,
    StockInsuficiente,
    EstadoNoDeclarado,
    OrdenNoEncontrada,
    SinPermisoSobreLaOrden,
    SinFichaDeCliente,
    PaginaFueraDeRango,
)


def _traducir(error: Exception) -> HTTPException:
    """Traduce un error de dominio al estado HTTP que le corresponde.

    El mensaje es el del error de dominio, que nunca incluye nombres de tablas,
    columnas ni restricciones (RN-18). Un vehículo o un repuesto no disponible y
    un catálogo vacío son ``409``: el cuerpo es válido y el conflicto es con el
    estado del dominio. Un estado no declarado y una página fuera de rango son
    ``422``. ``SinPermisoSobreLaOrden`` es ``403`` y una orden inexistente,
    ``404``.
    """
    if isinstance(error, OrdenNoEncontrada):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    if isinstance(error, SinPermisoSobreLaOrden):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        )
    if isinstance(error, SinFichaDeCliente):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        )
    if isinstance(error, EstadoNoDeclarado):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )
    if isinstance(
        error,
        (
            CatalogoDeEstadosVacio,
            VehiculoNoDisponible,
            RepuestoNoDisponible,
            TransicionNoPermitida,
            StockInsuficiente,
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


@router_ordenes.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrdenDetalleResponse,
)
async def alta_de_orden(
    datos: AltaOrdenRequest,
    actor: AltaDep,
    session: SessionDep,
) -> OrdenDetalleResponse:
    """Registra una orden de trabajo para un vehículo vigente.

    La habilitan ``ADMIN`` y ``RECEPCION``. La respuesta ``201`` trae los
    precios copiados, el total calculado y la primera línea de historial.
    """
    try:
        return await crear_orden(
            UnitOfWork(session),
            datos=datos,
            actor=actor,
        )
    except ERRORES_DE_ORDENES as error:
        raise _traducir(error) from error


@router_ordenes.get(
    "",
    response_model=PaginaResponse[OrdenResumenResponse],
)
async def listado_de_ordenes(
    actor: PersonalDep,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    estado: Annotated[str | None, Query(max_length=30)] = None,
) -> PaginaResponse[OrdenResumenResponse]:
    """Devuelve una página de órdenes, con filtro opcional por estado."""
    del actor  # Autoriza la dependencia; el listado no usa la cuenta actuante.
    parametros = ParametrosPagina(page=page, size=size)
    try:
        pagina = await listar_ordenes(
            UnitOfWork(session),
            parametros=parametros,
            estado=estado,
        )
    except ERRORES_DE_ORDENES as error:
        raise _traducir(error) from error

    return PaginaResponse[OrdenResumenResponse](
        items=pagina.items,
        total=pagina.total,
        page=pagina.page,
        size=pagina.size,
        pages=pagina.pages,
    )


@router_mis_ordenes.get(
    "/mis-ordenes",
    response_model=PaginaResponse[OrdenResumenResponse],
)
async def listado_de_mis_ordenes(
    actor: CurrentUser,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaResponse[OrdenResumenResponse]:
    """Devuelve las órdenes asociadas a los vehículos del cliente autenticado."""
    parametros = ParametrosPagina(page=page, size=size)
    try:
        pagina = await listar_mis_ordenes(
            UnitOfWork(session),
            actor=actor,
            parametros=parametros,
        )
    except ERRORES_DE_ORDENES as error:
        raise _traducir(error) from error

    return PaginaResponse[OrdenResumenResponse](
        items=pagina.items,
        total=pagina.total,
        page=pagina.page,
        size=pagina.size,
        pages=pagina.pages,
    )


@router_ordenes.get(
    "/{orden_id}",
    response_model=OrdenDetalleResponse,
)
async def detalle_de_orden(
    orden_id: int,
    actor: CurrentUser,
    session: SessionDep,
) -> OrdenDetalleResponse:
    """Devuelve el detalle de una orden a personal o al dueño del vehículo.

    La ruta sólo exige sesión: qué cuentas pueden ver la orden lo decide el
    servicio. Un ``404`` gana sobre un ``403`` para no revelar la existencia de
    órdenes ajenas.
    """
    try:
        return await consultar_orden(
            UnitOfWork(session),
            orden_id=orden_id,
            actor=actor,
        )
    except ERRORES_DE_ORDENES as error:
        raise _traducir(error) from error


@router_ordenes.post(
    "/{orden_id}/iniciar",
    response_model=OrdenDetalleResponse,
)
async def iniciar_orden_de_trabajo(
    orden_id: int,
    actor: MecanicoDep,
    session: SessionDep,
) -> OrdenDetalleResponse:
    """Inicia una orden ``PENDIENTE`` y la asigna al mecánico autenticado.

    Sólo el rol ``MECANICO`` llega al servicio: la dependencia responde ``403``
    antes de consultar la orden. Después mandan el ``404`` y el ``409``.
    """
    try:
        return await iniciar_orden(
            UnitOfWork(session),
            orden_id=orden_id,
            actor=actor,
        )
    except ERRORES_DE_ORDENES as error:
        raise _traducir(error) from error


@router_ordenes.post(
    "/{orden_id}/terminar",
    response_model=OrdenDetalleResponse,
)
async def terminar_orden_de_trabajo(
    orden_id: int,
    tareas: BackgroundTasks,
    actor: TerminarDep,
    session: SessionDep,
) -> OrdenDetalleResponse:
    """Termina una orden y consume el stock de sus ítems.

    La regla fina (``ADMIN`` o el mecánico asignado) la aplica el servicio
    después del ``404`` y antes del ``409``. El aviso simulado al cliente se
    agenda sólo cuando el servicio retornó, es decir, cuando la unidad de
    trabajo ya confirmó; nunca altera el resultado HTTP.
    """
    try:
        respuesta = await terminar_orden(
            UnitOfWork(session),
            orden_id=orden_id,
            actor=actor,
        )
    except ERRORES_DE_ORDENES as error:
        raise _traducir(error) from error

    tareas.add_task(avisar_terminacion, orden_id)
    return respuesta


@router_ordenes.post(
    "/{orden_id}/cancelar",
    response_model=OrdenDetalleResponse,
)
async def cancelar_orden_de_trabajo(
    orden_id: int,
    actor: CurrentUser,
    session: SessionDep,
) -> OrdenDetalleResponse:
    """Cancela una orden ``PENDIENTE`` a pedido del personal o de su dueño.

    La ruta sólo exige sesión: el servicio evalúa el permiso antes que el
    estado y responde ``403``, ``409`` o ``404`` según corresponda.
    """
    try:
        return await cancelar_orden(
            UnitOfWork(session),
            orden_id=orden_id,
            actor=actor,
        )
    except ERRORES_DE_ORDENES as error:
        raise _traducir(error) from error


@router_estados_orden.get(
    "",
    response_model=list[EstadoOrdenResponse],
)
async def catalogo_de_estados(
    actor: CurrentUser,
    session: SessionDep,
) -> list[EstadoOrdenResponse]:
    """Devuelve el catálogo de estados ordenado por posición.

    Lo puede consultar cualquier cuenta autenticada. No hay rutas de escritura:
    el catálogo lo carga ``seed.py`` y la API sólo lo lee.
    """
    del actor  # Autoriza la sesión; el catálogo no depende de la cuenta.
    return await listar_estados(UnitOfWork(session))
