"""Contratos de entrada y salida del módulo de repuestos.

Los contratos de entrada usan ``extra="forbid"``: un campo que el contrato no
declara es un error de validación, no un dato ignorado. El ``PATCH`` declara
sólo ``descripcion`` y ``precio``, así que un ``stock`` en el cuerpo es un
``422`` del contrato: las existencias sólo cambian por alta, reposición o
consumo de una orden (C-07).

El código se normaliza (``strip`` + ``upper``) antes de persistir para que el
índice único parcial cubra mayúsculas y espacios circundantes. El precio se
modela con ``Decimal`` acotado a ``NUMERIC(10, 2)`` positivo, y no se cuantiza
a mano: el contrato ya rechaza más de dos decimales. Los contratos de salida se
construyen desde las entidades con ``model_validate(..., from_attributes=True)``
y no exponen la marca de baja.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "AltaRepuestoRequest",
    "EditarRepuestoRequest",
    "HistorialPrecioResponse",
    "MovimientoStockResponse",
    "ReponerRequest",
    "RepuestoResponse",
]


class AltaRepuestoRequest(BaseModel):
    """Datos del alta de un repuesto, con su stock inicial."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(max_length=50)
    descripcion: str = Field(max_length=200)
    precio: Decimal = Field(max_digits=10, decimal_places=2, gt=0)
    stock: int = Field(default=0, ge=0)

    @field_validator("codigo")
    @classmethod
    def _normalizar_codigo(cls, valor: str) -> str:
        """Normaliza el código sin distinguir mayúsculas ni espacios."""
        return valor.strip().upper()


class EditarRepuestoRequest(BaseModel):
    """Campos editables de un repuesto vigente.

    No declara ``codigo`` ni ``stock`` a propósito: el código identifica al
    repuesto y el stock sólo cambia por movimientos auditables.
    """

    model_config = ConfigDict(extra="forbid")

    descripcion: str | None = Field(default=None, max_length=200)
    precio: Decimal | None = Field(
        default=None,
        max_digits=10,
        decimal_places=2,
        gt=0,
    )


class ReponerRequest(BaseModel):
    """Cantidad de unidades que se suman al stock de un repuesto."""

    model_config = ConfigDict(extra="forbid")

    cantidad: int = Field(gt=0)


class RepuestoResponse(BaseModel):
    """Ficha de un repuesto vigente, sin su marca de baja."""

    model_config = ConfigDict(extra="forbid")

    id: int
    codigo: str
    descripcion: str
    precio: Decimal
    stock: int


class MovimientoStockResponse(BaseModel):
    """Movimiento de stock de sólo agregado, con su actor y su motivo."""

    model_config = ConfigDict(extra="forbid")

    id: int
    repuesto_id: int
    orden_id: int | None
    usuario_id: int
    cantidad: int
    motivo: str
    cuando: datetime


class HistorialPrecioResponse(BaseModel):
    """Línea de historial de un cambio efectivo de precio."""

    model_config = ConfigDict(extra="forbid")

    id: int
    repuesto_id: int
    usuario_id: int
    precio_anterior: Decimal
    precio_nuevo: Decimal
    cuando: datetime
