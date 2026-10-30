"""Errores de dominio del módulo de órdenes de trabajo.

El servicio lanza estos errores y el router los traduce a ``403``, ``404``,
``409`` y ``422``. Ningún mensaje incluye nombres de tablas, columnas,
restricciones ni índices (RN-18): el cliente se entera de qué regla falló, no
de cómo está armada la base. Cada error es una clase distinta para que el
router le asigne su estado sin inspeccionar el texto.
"""

from __future__ import annotations

__all__ = [
    "CatalogoDeEstadosVacio",
    "ErrorOrdenes",
    "EstadoNoDeclarado",
    "OrdenNoEncontrada",
    "RepuestoNoDisponible",
    "SinPermisoSobreLaOrden",
    "StockInsuficiente",
    "TransicionNoPermitida",
    "VehiculoNoDisponible",
]


class ErrorOrdenes(Exception):
    """Base de los errores de dominio del módulo de órdenes de trabajo."""

    def __init__(self, mensaje: str) -> None:
        self.mensaje = mensaje
        super().__init__(mensaje)

    def __str__(self) -> str:
        """Devuelve el mensaje tal como se mostrará al cliente."""
        return self.mensaje


class OrdenNoEncontrada(ErrorOrdenes):
    """No existe una orden con el identificador indicado."""

    def __init__(self, mensaje: str = "La orden no existe.") -> None:
        super().__init__(mensaje)


class VehiculoNoDisponible(ErrorOrdenes):
    """El vehículo no existe o fue dado de baja."""

    def __init__(
        self,
        mensaje: str = "El vehículo no existe o está dado de baja.",
    ) -> None:
        super().__init__(mensaje)


class RepuestoNoDisponible(ErrorOrdenes):
    """Al menos uno de los repuestos no existe o fue dado de baja."""

    def __init__(
        self,
        mensaje: str = (
            "Uno o más repuestos no existen o están dados de baja."
        ),
    ) -> None:
        super().__init__(mensaje)


class CatalogoDeEstadosVacio(ErrorOrdenes):
    """El catálogo de estados no tiene filas para asignar a la orden."""

    def __init__(
        self,
        mensaje: str = "El catálogo de estados está vacío.",
    ) -> None:
        super().__init__(mensaje)


class EstadoNoDeclarado(ErrorOrdenes):
    """El código indicado no pertenece al catálogo de estados."""

    def __init__(
        self,
        mensaje: str = "El estado indicado no existe en el catálogo.",
    ) -> None:
        super().__init__(mensaje)


class TransicionNoPermitida(ErrorOrdenes):
    """El estado actual no admite la transición pedida."""

    def __init__(
        self,
        mensaje: str = "La orden no permite esa transición de estado.",
    ) -> None:
        super().__init__(mensaje)


class StockInsuficiente(ErrorOrdenes):
    """Al menos un repuesto de la orden no tiene stock para consumirse."""

    def __init__(
        self,
        mensaje: str = "No hay stock suficiente para completar la orden.",
    ) -> None:
        super().__init__(mensaje)


class SinPermisoSobreLaOrden(ErrorOrdenes):
    """La cuenta no es personal habilitado ni dueña del vehículo."""

    def __init__(
        self,
        mensaje: str = "No tenés permiso sobre esta orden.",
    ) -> None:
        super().__init__(mensaje)
