"""Errores de dominio del módulo de clientes.

El servicio lanza estos errores y el router los traduce a ``403``, ``404``,
``409`` y ``422``. Ningún mensaje incluye nombres de tablas, columnas,
restricciones ni índices (RN-18): el cliente se entera de qué regla falló, no
de cómo está armada la base.
"""

from __future__ import annotations

__all__ = [
    "AnioFueraDeRango",
    "ClienteNoEncontrado",
    "DocumentoYaRegistrado",
    "ErrorClientes",
    "PatenteYaRegistrada",
    "SinFichaDeCliente",
    "VehiculoConOrdenesAbiertas",
    "VehiculoNoEncontrado",
]


class ErrorClientes(Exception):
    """Base de los errores de dominio del módulo de clientes."""


class ClienteNoEncontrado(ErrorClientes):
    """No existe una ficha con el identificador indicado."""

    def __init__(self, mensaje: str = "No se encontró el cliente indicado") -> None:
        super().__init__(mensaje)


class DocumentoYaRegistrado(ErrorClientes):
    """El documento ya pertenece a otra ficha de cliente."""

    def __init__(
        self,
        mensaje: str = "El documento indicado ya está registrado",
    ) -> None:
        super().__init__(mensaje)


class VehiculoNoEncontrado(ErrorClientes):
    """No existe un vehículo vigente con el identificador indicado."""

    def __init__(self, mensaje: str = "No se encontró el vehículo indicado") -> None:
        super().__init__(mensaje)


class PatenteYaRegistrada(ErrorClientes):
    """Otro vehículo vigente ya usa esa patente."""

    def __init__(
        self,
        mensaje: str = "La patente indicada ya pertenece a un vehículo vigente",
    ) -> None:
        super().__init__(mensaje)


class VehiculoConOrdenesAbiertas(ErrorClientes):
    """El vehículo tiene órdenes de trabajo que impiden darlo de baja."""

    def __init__(
        self,
        mensaje: str = "El vehículo tiene órdenes de trabajo abiertas",
    ) -> None:
        super().__init__(mensaje)


class SinFichaDeCliente(ErrorClientes):
    """La cuenta autenticada no tiene una ficha de cliente asociada."""

    def __init__(
        self,
        mensaje: str = "La cuenta no tiene una ficha de cliente asociada",
    ) -> None:
        super().__init__(mensaje)


class AnioFueraDeRango(ErrorClientes):
    """El año de fabricación no está dentro del rango admitido."""

    def __init__(
        self,
        mensaje: str = "El año debe estar entre 1950 y 2100",
    ) -> None:
        super().__init__(mensaje)
