"""Contratos de entrada y salida del módulo de órdenes de trabajo.

Los contratos de entrada usan ``extra="forbid"``: el alta declara sólo el
vehículo, la falla y los ítems. Un ``precio``, un ``total``, un ``estado`` o
un ``mecanico_id`` en el cuerpo es un ``422`` del contrato, porque el precio se
copia del repuesto, el total lo calcula el servidor y el mecánico se asigna al
iniciar la orden. Un validador rechaza dos ítems del mismo repuesto antes de
tocar la base; la restricción de unicidad queda como última red.

Los contratos de salida no se arman con cargas perezosas: el repositorio
entrega las filas ya resueltas y estas funciones las mapean. El dinero viaja
como ``Decimal`` y nunca como ``float``.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.ordenes.repository import (
    DetalleOrdenFila,
    FilaItemOrden,
    FilaOrdenResumen,
)

__all__ = [
    "AltaOrdenRequest",
    "ClienteOrdenResponse",
    "EstadoOrdenResponse",
    "HistorialEstadoResponse",
    "ItemOrdenRequest",
    "ItemOrdenResponse",
    "OrdenDetalleResponse",
    "OrdenResumenResponse",
    "VehiculoOrdenResponse",
    "detalle_desde_fila",
    "resumen_desde_fila",
]


class ItemOrdenRequest(BaseModel):
    """Repuesto pedido en el alta, con la cantidad solicitada."""

    model_config = ConfigDict(extra="forbid")

    repuesto_id: int
    cantidad: int = Field(gt=0)


class AltaOrdenRequest(BaseModel):
    """Datos del alta de una orden: vehículo, falla e ítems.

    La falla es obligatoria y el servidor exige al menos un ítem. El precio y
    el total no se reciben: salen de los repuestos vigentes.
    """

    model_config = ConfigDict(extra="forbid")

    vehiculo_id: int
    falla: str = Field(min_length=1, max_length=500)
    items: list[ItemOrdenRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def _rechazar_repuestos_repetidos(self) -> AltaOrdenRequest:
        """Exige un repuesto distinto por orden, como el dominio."""
        vistos: set[int] = set()
        for item in self.items:
            if item.repuesto_id in vistos:
                raise ValueError(
                    f"El repuesto {item.repuesto_id} aparece más de una vez "
                    "en la orden"
                )
            vistos.add(item.repuesto_id)
        return self


class EstadoOrdenResponse(BaseModel):
    """Estado del catálogo, tal como lo expone la API."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    codigo: str
    descripcion: str
    posicion: int
    es_final: bool


class ItemOrdenResponse(BaseModel):
    """Ítem de una orden con la descripción del repuesto y el precio copiado."""

    model_config = ConfigDict(extra="forbid")

    id: int
    repuesto_id: int
    descripcion: str
    cantidad: int
    precio_unitario: Decimal


class HistorialEstadoResponse(BaseModel):
    """Línea de historial de una transición de estado."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    desde_estado: str | None
    hasta_estado: str
    usuario_id: int
    cuando: datetime


class VehiculoOrdenResponse(BaseModel):
    """Vehículo de la orden, sin su marca de baja."""

    model_config = ConfigDict(extra="forbid")

    id: int
    patente: str
    marca: str
    modelo: str
    anio: int


class ClienteOrdenResponse(BaseModel):
    """Ficha del cliente dueño del vehículo de la orden."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nombre: str
    documento: str
    telefono: str | None


class OrdenResumenResponse(BaseModel):
    """Fila del listado de órdenes, con la patente de su vehículo."""

    model_config = ConfigDict(extra="forbid")

    id: int
    vehiculo_id: int
    patente: str
    estado: str
    mecanico_id: int | None
    falla: str
    total: Decimal
    creada_en: datetime


class OrdenDetalleResponse(BaseModel):
    """Detalle de una orden con vehículo, cliente, ítems e historial."""

    model_config = ConfigDict(extra="forbid")

    id: int
    vehiculo: VehiculoOrdenResponse
    cliente: ClienteOrdenResponse
    estado: str
    mecanico_id: int | None
    mecanico_nombre: str | None
    falla: str
    total: Decimal
    creada_en: datetime
    items: list[ItemOrdenResponse]
    historial: list[HistorialEstadoResponse]


def resumen_desde_fila(fila: FilaOrdenResumen) -> OrdenResumenResponse:
    """Arma la fila del listado a partir de la orden y la patente resueltas.

    El repositorio ya trae la patente con un ``JOIN``; acá sólo se eligen los
    campos del contrato para no exponer la marca de baja del vehículo.
    """
    orden = fila.orden
    return OrdenResumenResponse(
        id=orden.id,
        vehiculo_id=orden.vehiculo_id,
        patente=fila.patente,
        estado=orden.estado,
        mecanico_id=orden.mecanico_id,
        falla=orden.falla,
        total=orden.total,
        creada_en=orden.creada_en,
    )


def _item_desde_fila(fila: FilaItemOrden) -> ItemOrdenResponse:
    """Arma un ítem con la descripción del repuesto y el precio copiado."""
    return ItemOrdenResponse(
        id=fila.item.id,
        repuesto_id=fila.item.repuesto_id,
        descripcion=fila.repuesto.descripcion,
        cantidad=fila.item.cantidad,
        precio_unitario=fila.item.precio_unitario,
    )


def detalle_desde_fila(fila: DetalleOrdenFila) -> OrdenDetalleResponse:
    """Arma el detalle completo a partir de las filas ya resueltas.

    El repositorio entrega la orden con su vehículo, cliente y mecánico, los
    ítems con su repuesto y el historial en orden cronológico. El nombre del
    mecánico es nulo mientras la orden no tenga asignación.
    """
    orden = fila.orden
    return OrdenDetalleResponse(
        id=orden.id,
        vehiculo=VehiculoOrdenResponse(
            id=fila.vehiculo.id,
            patente=fila.vehiculo.patente,
            marca=fila.vehiculo.marca,
            modelo=fila.vehiculo.modelo,
            anio=fila.vehiculo.anio,
        ),
        cliente=ClienteOrdenResponse(
            id=fila.cliente.id,
            nombre=fila.cliente.nombre,
            documento=fila.cliente.documento,
            telefono=fila.cliente.telefono,
        ),
        estado=orden.estado,
        mecanico_id=orden.mecanico_id,
        mecanico_nombre=(
            fila.mecanico.nombre if fila.mecanico is not None else None
        ),
        falla=orden.falla,
        total=orden.total,
        creada_en=orden.creada_en,
        items=[_item_desde_fila(item) for item in fila.items],
        historial=[
            HistorialEstadoResponse.model_validate(
                linea,
                from_attributes=True,
            )
            for linea in fila.historial
        ],
    )
