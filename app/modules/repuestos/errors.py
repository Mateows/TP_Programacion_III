"""Errores de dominio del módulo de repuestos.

El servicio lanza estos errores y el router los traduce a ``404`` y ``409``.
Ningún mensaje incluye nombres de tablas, columnas, restricciones ni índices
(RN-18): el cliente se entera de qué regla falló, no de cómo está armada la
base.
"""

from __future__ import annotations

__all__ = [
    "CodigoYaRegistrado",
    "ErrorRepuestos",
    "PrecioNoAumenta",
    "RepuestoNoEncontrado",
]


class ErrorRepuestos(Exception):
    """Base de los errores de dominio del módulo de repuestos."""


class RepuestoNoEncontrado(ErrorRepuestos):
    """No existe un repuesto vigente con el identificador indicado."""

    def __init__(
        self,
        mensaje: str = "No se encontró el repuesto indicado",
    ) -> None:
        super().__init__(mensaje)


class CodigoYaRegistrado(ErrorRepuestos):
    """Otro repuesto vigente ya usa ese código."""

    def __init__(
        self,
        mensaje: str = "El código indicado ya pertenece a un repuesto vigente",
    ) -> None:
        super().__init__(mensaje)


class PrecioNoAumenta(ErrorRepuestos):
    """El precio nuevo no es mayor que el vigente.

    El precio sólo sube: un valor igual es un no-op que no deja historial y un
    valor menor se rechaza antes de escribir.
    """

    def __init__(
        self,
        mensaje: str = "El precio nuevo debe aumentar el precio vigente",
    ) -> None:
        super().__init__(mensaje)
