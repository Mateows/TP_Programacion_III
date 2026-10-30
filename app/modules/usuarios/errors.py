"""Errores de dominio del módulo de usuarios.

El servicio lanza estos errores y el router los traduce a ``404``, ``409`` y
``422``. Ningún mensaje incluye nombres de tablas, columnas o restricciones
(RN-18): el cliente se entera de qué regla falló, no de cómo está armada la
base.

``CorreoYaRegistrado`` y ``PasswordInvalida`` se reexportan desde el módulo de
autenticación: la regla de correo único y el límite de 72 bytes de bcrypt son
los mismos para el auto-registro y para el alta de personal, y duplicar las
clases haría que las dos reglas diverjan.

``PaginaFueraDeRango`` se reexporta desde ``app.core.paginacion``: la
comparten los tres listados paginados del proyecto. Como ya no puede heredar
de ``ErrorUsuarios`` sin acoplar ``core`` a este módulo, se registra como
subclase virtual para que siga siendo un error de dominio de usuarios para
quien capture la base del módulo.
"""

from __future__ import annotations

from abc import ABCMeta

from app.core.paginacion import PaginaFueraDeRango
from app.modules.auth.errors import CorreoYaRegistrado, PasswordInvalida

__all__ = [
    "AsignacionNoEncontrada",
    "CorreoYaRegistrado",
    "ErrorUsuarios",
    "PaginaFueraDeRango",
    "PasswordInvalida",
    "RevocacionPropiaNoPermitida",
    "RolNoAsignable",
    "RolYaAsignado",
    "UltimoAdministrador",
    "UsuarioNoEncontrado",
    "VencimientoInvalido",
]


class ErrorUsuarios(Exception, metaclass=ABCMeta):
    """Base de los errores de dominio del módulo de usuarios."""



class UsuarioNoEncontrado(ErrorUsuarios):
    """No existe una cuenta con el identificador indicado."""

    def __init__(self, mensaje: str = "No se encontró el usuario indicado") -> None:
        super().__init__(mensaje)


class AsignacionNoEncontrada(ErrorUsuarios):
    """El usuario no tiene una asignación abierta de ese rol."""

    def __init__(
        self,
        mensaje: str = "No se encontró una asignación abierta de ese rol",
    ) -> None:
        super().__init__(mensaje)


class RolYaAsignado(ErrorUsuarios):
    """El usuario ya tiene una asignación abierta y vigente de ese rol.

    La asignación existente se informa por su rol, nunca por su ``id``: el
    identificador de fila no le sirve al cliente y no debe salir del servicio.
    """

    def __init__(self, rol: str) -> None:
        super().__init__(
            f"El usuario ya tiene una asignación abierta del rol {rol}"
        )


class RevocacionPropiaNoPermitida(ErrorUsuarios):
    """Un administrador no puede revocar su propia asignación ``ADMIN``.

    Se evalúa antes que la invariante del último administrador para que el
    mensaje sea el correcto cuando ambas condiciones se cumplen a la vez.
    """

    def __init__(
        self,
        mensaje: str = "Un administrador no puede revocar su propia asignación de rol",
    ) -> None:
        super().__init__(mensaje)


class UltimoAdministrador(ErrorUsuarios):
    """La revocación dejaría el sistema sin administradores vigentes."""

    def __init__(
        self,
        mensaje: str = "La operación dejaría el sistema sin administradores vigentes",
    ) -> None:
        super().__init__(mensaje)


class RolNoAsignable(ErrorUsuarios):
    """El rol no se otorga desde la administración.

    ``CLIENTE`` nace con el auto-registro, que además crea la ficha de cliente
    (RN-02); el resto del catálogo se rechaza por no existir.
    """

    def __init__(self, rol: str) -> None:
        super().__init__(
            f"El rol {rol} no se puede asignar desde la administración"
        )


class VencimientoInvalido(ErrorUsuarios):
    """El vencimiento pedido no es futuro o carece de zona horaria."""

    def __init__(
        self,
        mensaje: str = "El vencimiento debe ser futuro y con zona horaria",
    ) -> None:
        super().__init__(mensaje)


# El error de paginación se define en ``core.paginacion``; se registra como
# subclase virtual para conservar ``isinstance(error, ErrorUsuarios)``.
ErrorUsuarios.register(PaginaFueraDeRango)

