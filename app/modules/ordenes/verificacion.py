"""Verificador real de órdenes de trabajo abiertas para la baja de vehículo.

RN-16 impide dar de baja un vehículo que tenga al menos una orden en un estado
que el catálogo ``estado_orden`` no marca como final. Este verificador es la
implementación concreta del protocolo ``VerificadorOrdenesAbiertas`` que declara
el módulo de clientes: la consulta une ``orden_trabajo`` con ``estado_orden`` y
cuenta sólo las órdenes no finales del vehículo indicado.

Es de sólo lectura: no escribe ni confirma. La confirmación pertenece a la
unidad de trabajo que administra la baja del vehículo.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clientes.verificacion import VerificadorOrdenesAbiertas
from app.modules.ordenes.models import EstadoOrden, OrdenTrabajo

__all__ = ["VerificadorOrdenesAbiertasSQL"]


class VerificadorOrdenesAbiertasSQL:
    """Cuenta las órdenes abiertas de un vehículo contra la base de datos."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def contar_abiertas(self, vehiculo_id: int) -> int:
        """Devuelve cuántas órdenes del vehículo están en un estado no final.

        El vehículo viaja como parámetro ligado, nunca interpolado en el SQL.
        Una orden cuyo estado no exista en el catálogo no puede evaluarse como
        abierta ni como final; la FK de ``orden_trabajo.estado`` impide ese caso
        en la base.
        """
        sentencia = (
            select(func.count())
            .select_from(OrdenTrabajo)
            .join(
                EstadoOrden,
                EstadoOrden.codigo == OrdenTrabajo.estado,
            )
            .where(
                OrdenTrabajo.vehiculo_id == vehiculo_id,
                EstadoOrden.es_final.is_(False),
            )
        )
        resultado = await self._session.scalars(sentencia)
        return int(resultado.first() or 0)
