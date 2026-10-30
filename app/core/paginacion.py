"""Contrato de paginación compartido por los listados de la API.

El envoltorio ``{items, total, page, size, pages}`` es el mismo para todos los
listados del proyecto: la página empieza en 1, el tamaño va de 1 a 100 y el
valor por defecto es 20. ``pages`` se calcula sobre el total de filas, no sobre
la cantidad devuelta: una página fuera de rango sigue informando cuántas
páginas existen en realidad.

``PaginaResponse`` y ``PaginaFueraDeRango`` viven acá —y no en un módulo de
dominio— para que los listados de usuarios, repuestos y órdenes compartan un
único objeto sin acoplar sus módulos entre sí.
"""

import math
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

PAGINA_INICIAL = 1
TAMANO_POR_DEFECTO = 20
TAMANO_MINIMO = 1
TAMANO_MAXIMO = 100


@dataclass(frozen=True)
class ParametrosPagina:
    """Página y tamaño solicitados, ya validados.

    Se construye desde los parámetros de consulta del router; la validación
    vive acá para que los tests la ejerciten sin levantar FastAPI.
    """

    page: int = PAGINA_INICIAL
    size: int = TAMANO_POR_DEFECTO

    def __post_init__(self) -> None:
        if self.page < PAGINA_INICIAL:
            raise ValueError(
                f"La página debe ser mayor o igual a {PAGINA_INICIAL}"
            )
        if not TAMANO_MINIMO <= self.size <= TAMANO_MAXIMO:
            raise ValueError(
                f"El tamaño de página debe estar entre {TAMANO_MINIMO} y "
                f"{TAMANO_MAXIMO}"
            )

    @property
    def offset(self) -> int:
        """Filas a saltear para llegar al comienzo de la página pedida."""
        return (self.page - 1) * self.size


@dataclass(frozen=True)
class Pagina(Generic[T]):
    """Página de resultados con el total y la cantidad de páginas."""

    items: list[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        """Cantidad total de páginas; cero cuando no hay filas."""
        if self.total <= 0:
            return 0
        return math.ceil(self.total / self.size)


def construir_pagina(
    items: list[T],
    total: int,
    parametros: ParametrosPagina,
) -> Pagina[T]:
    """Arma la página con los elementos ya recortados y el total de filas."""
    return Pagina(
        items=items,
        total=total,
        page=parametros.page,
        size=parametros.size,
    )


class PaginaResponse(BaseModel, Generic[T]):
    """Página de resultados con el total y la cantidad de páginas."""

    model_config = ConfigDict(extra="forbid")

    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class PaginaFueraDeRango(Exception):
    """La página pedida supera la última disponible.

    ``pages`` puede ser cero cuando no hay filas; el mensaje lo dice sin
    inventar una página vacía. No hereda de los errores de un módulo de
    dominio: la comparten todos los listados paginados del proyecto.
    """

    def __init__(self, page: int, pages: int) -> None:
        self.page = page
        self.pages = pages
        if pages == 0:
            super().__init__(
                f"La página {page} no existe: no hay resultados disponibles"
            )
        else:
            super().__init__(
                f"La página {page} supera la última página disponible ({pages})"
            )
