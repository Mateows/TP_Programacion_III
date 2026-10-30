"""Rutas HTTP del catálogo de repuestos.

El router no conoce reglas de negocio: recibe la sesión y la cuenta actuante,
delega en ``service.py`` y traduce los errores de dominio a ``404``, ``409`` y
``422``. El ``401`` y el ``403`` por cambio de contraseña los resuelve
``router_protegido``; el ``403`` por rol, la dependencia de cada ruta.

La lectura del catálogo la habilita cualquier rol del taller (``ADMIN``,
``RECEPCION``, ``MECANICO``); administrar repuestos es exclusivo de ``ADMIN``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioAutenticado, requiere_rol
from app.core.paginacion import PaginaFueraDeRango, PaginaResponse, ParametrosPagina
from app.core.repository import ConflictoDeIntegridad
from app.core.unit_of_work import UnitOfWork
from app.modules.repuestos.errors import (
    CodigoYaRegistrado,
    PrecioNoAumenta,
    RepuestoNoEncontrado,
)
from app.modules.repuestos.models import Repuesto
from app.modules.repuestos.schemas import (
    AltaRepuestoRequest,
    EditarRepuestoRequest,
    HistorialPrecioResponse,
    MovimientoStockResponse,
    ReponerRequest,
    RepuestoResponse,
)
from app.modules.repuestos.service import (
    consultar_movimientos,
    consultar_precios,
    crear_repuesto,
    dar_de_baja_repuesto,
    editar_repuesto,
    listar_repuestos,
    reponer_stock,
)

router_repuestos = APIRouter(tags=["repuestos"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PersonalDep = Annotated[
    UsuarioAutenticado,
    Depends(requiere_rol("ADMIN", "RECEPCION", "MECANICO")),
]
AdminDep = Annotated[UsuarioAutenticado, Depends(requiere_rol("ADMIN"))]

# Todos los errores de dominio del módulo, para no repetir la tupla en cada
# ruta. La traducción a estado vive en ``_traducir``.
ERRORES_DE_REPUESTOS = (
    RepuestoNoEncontrado,
    CodigoYaRegistrado,
    PrecioNoAumenta,
    PaginaFueraDeRango,
    ConflictoDeIntegridad,
)


def _traducir(error: Exception) -> HTTPException:
    """Traduce un error de dominio al estado HTTP que le corresponde.

    El mensaje es el del error de dominio, que nunca incluye nombres de tablas,
    columnas ni restricciones (RN-18). Un precio que no aumenta es un ``409``:
    el cuerpo es válido y el conflicto es con la regla del dominio.
    """
    if isinstance(error, RepuestoNoEncontrado):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    if isinstance(
        error,
        (CodigoYaRegistrado, PrecioNoAumenta, ConflictoDeIntegridad),
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(error),
    )


def _repuesto(entidad: Repuesto) -> RepuestoResponse:
    """Convierte la entidad de tabla al contrato de salida del repuesto."""
    return RepuestoResponse.model_validate(entidad, from_attributes=True)


@router_repuestos.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RepuestoResponse,
)
async def alta_de_repuesto(
    datos: AltaRepuestoRequest,
    actor: AdminDep,
    session: SessionDep,
) -> RepuestoResponse:
    """Da de alta un repuesto con su stock inicial (sólo ``ADMIN``)."""
    try:
        repuesto = await crear_repuesto(UnitOfWork(session), datos, actor.usuario)
    except ERRORES_DE_REPUESTOS as error:
        raise _traducir(error) from error

    return _repuesto(repuesto)


@router_repuestos.get(
    "",
    response_model=PaginaResponse[RepuestoResponse],
)
async def listado_de_repuestos(
    actor: PersonalDep,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> PaginaResponse[RepuestoResponse]:
    """Devuelve una página del catálogo vigente, con búsqueda por descripción."""
    del actor  # Autoriza la dependencia; el listado no usa la cuenta actuante.
    parametros = ParametrosPagina(page=page, size=size)
    try:
        pagina = await listar_repuestos(UnitOfWork(session), parametros, texto=q)
    except ERRORES_DE_REPUESTOS as error:
        raise _traducir(error) from error

    return PaginaResponse[RepuestoResponse](
        items=[_repuesto(repuesto) for repuesto in pagina.items],
        total=pagina.total,
        page=pagina.page,
        size=pagina.size,
        pages=pagina.pages,
    )


@router_repuestos.patch(
    "/{repuesto_id}",
    response_model=RepuestoResponse,
)
async def edicion_de_repuesto(
    repuesto_id: int,
    datos: EditarRepuestoRequest,
    actor: AdminDep,
    session: SessionDep,
) -> RepuestoResponse:
    """Actualiza descripción y/o precio de un repuesto vigente (sólo ``ADMIN``)."""
    try:
        repuesto = await editar_repuesto(
            UnitOfWork(session),
            repuesto_id,
            datos,
            actor.usuario,
        )
    except ERRORES_DE_REPUESTOS as error:
        raise _traducir(error) from error

    return _repuesto(repuesto)


@router_repuestos.post(
    "/{repuesto_id}/reponer",
    response_model=RepuestoResponse,
)
async def reposicion_de_stock(
    repuesto_id: int,
    datos: ReponerRequest,
    actor: AdminDep,
    session: SessionDep,
) -> RepuestoResponse:
    """Suma stock a un repuesto vigente y deja su movimiento (sólo ``ADMIN``)."""
    try:
        repuesto = await reponer_stock(
            UnitOfWork(session),
            repuesto_id,
            datos.cantidad,
            actor.usuario,
        )
    except ERRORES_DE_REPUESTOS as error:
        raise _traducir(error) from error

    return _repuesto(repuesto)


@router_repuestos.get(
    "/{repuesto_id}/movimientos",
    response_model=list[MovimientoStockResponse],
)
async def movimientos_de_repuesto(
    repuesto_id: int,
    actor: AdminDep,
    session: SessionDep,
) -> list[MovimientoStockResponse]:
    """Lista los movimientos del repuesto, del más reciente al más antiguo."""
    del actor  # Autoriza la dependencia; la consulta no usa la cuenta actuante.
    try:
        movimientos = await consultar_movimientos(UnitOfWork(session), repuesto_id)
    except ERRORES_DE_REPUESTOS as error:
        raise _traducir(error) from error

    return [
        MovimientoStockResponse.model_validate(movimiento, from_attributes=True)
        for movimiento in movimientos
    ]


@router_repuestos.get(
    "/{repuesto_id}/precios",
    response_model=list[HistorialPrecioResponse],
)
async def precios_de_repuesto(
    repuesto_id: int,
    actor: AdminDep,
    session: SessionDep,
) -> list[HistorialPrecioResponse]:
    """Lista el historial de precios, del más reciente al más antiguo."""
    del actor  # Autoriza la dependencia; la consulta no usa la cuenta actuante.
    try:
        precios = await consultar_precios(UnitOfWork(session), repuesto_id)
    except ERRORES_DE_REPUESTOS as error:
        raise _traducir(error) from error

    return [
        HistorialPrecioResponse.model_validate(linea, from_attributes=True)
        for linea in precios
    ]


@router_repuestos.delete(
    "/{repuesto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def baja_de_repuesto(
    repuesto_id: int,
    actor: AdminDep,
    session: SessionDep,
) -> None:
    """Da de baja lógica un repuesto vigente (sólo ``ADMIN``).

    ``Response`` como clase de retorno deja el cuerpo vacío: el ``204`` no lleva
    entidad. La fila se conserva con su marca de baja y su historial.
    """
    del actor  # Autoriza la dependencia; el servicio no usa la cuenta actuante.
    try:
        await dar_de_baja_repuesto(UnitOfWork(session), repuesto_id)
    except ERRORES_DE_REPUESTOS as error:
        raise _traducir(error) from error
