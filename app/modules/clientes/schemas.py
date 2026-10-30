"""Contratos de entrada y salida del módulo de clientes.

Los contratos de entrada usan ``extra="forbid"``: un campo que el contrato no
declara es un error de validación. La patente se normaliza antes de persistir
para que el índice único parcial cubra mayúsculas y espacios circundantes; el
año se acota en el contrato además del ``CHECK`` de la base, para responder
``422`` en lugar de un error del motor.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

ANIO_MINIMO = 1950
ANIO_MAXIMO = 2100


class AltaClienteRequest(BaseModel):
    """Datos del alta de una ficha de cliente."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(max_length=150)
    documento: str = Field(max_length=50)
    telefono: str | None = Field(default=None, max_length=30)


class AltaVehiculoRequest(BaseModel):
    """Datos del alta de un vehículo para un cliente existente."""

    model_config = ConfigDict(extra="forbid")

    patente: str = Field(max_length=10)
    marca: str = Field(max_length=100)
    modelo: str = Field(max_length=100)
    anio: int

    @field_validator("patente")
    @classmethod
    def _normalizar_patente(cls, valor: str) -> str:
        """Normaliza la patente sin distinguir mayúsculas ni espacios."""
        return valor.strip().upper()

    @field_validator("anio")
    @classmethod
    def _validar_anio(cls, valor: int) -> int:
        """Exige un año de fabricación dentro del rango de la KB."""
        if not ANIO_MINIMO <= valor <= ANIO_MAXIMO:
            raise ValueError(
                f"El año debe estar entre {ANIO_MINIMO} y {ANIO_MAXIMO}"
            )
        return valor


class ClienteResponse(BaseModel):
    """Ficha de un cliente, con su vínculo opcional a una cuenta."""

    model_config = ConfigDict(extra="forbid")

    id: int
    usuario_id: int | None
    nombre: str
    documento: str
    telefono: str | None


class VehiculoResponse(BaseModel):
    """Datos de un vehículo vigente de un cliente."""

    model_config = ConfigDict(extra="forbid")

    id: int
    cliente_id: int
    patente: str
    marca: str
    modelo: str
    anio: int


class ClienteConVehiculosResponse(BaseModel):
    """Ficha del cliente junto con sus vehículos vigentes."""

    model_config = ConfigDict(extra="forbid")

    id: int
    usuario_id: int | None
    nombre: str
    documento: str
    telefono: str | None
    vehiculos: list[VehiculoResponse]
