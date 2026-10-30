"""Contrato de verificación de órdenes de trabajo abiertas.

La baja de vehículo (RN-16) sólo se permite si el vehículo no tiene órdenes en
un estado que el catálogo ``estado_orden`` no marca como final. El servicio de
clientes depende de este protocolo y no del módulo de órdenes: así el contrato
HTTP no se acopla a cómo se cuentan las órdenes.

La implementación real vive en ``app.modules.ordenes.verificacion``
(``VerificadorOrdenesAbiertasSQL``) y el router de clientes la inyecta al
servicio. Este módulo sólo declara el protocolo.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["VerificadorOrdenesAbiertas"]


@runtime_checkable
class VerificadorOrdenesAbiertas(Protocol):
    """Cuenta las órdenes de trabajo abiertas de un vehículo."""

    async def contar_abiertas(self, vehiculo_id: int) -> int: ...
