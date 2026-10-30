"""Repositorios del módulo de clientes.

``ClienteRepository`` atiende la ficha del taller; ``VehiculoRepository`` hereda
el borrado lógico, así que sus lecturas excluyen las filas dadas de baja y la
baja es idempotente. Ninguna consulta confirma: la confirmación pertenece a la
unidad de trabajo.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.clientes.models import Cliente, Vehiculo


class ClienteRepository(BaseRepository[Cliente]):
    """Fichas de los clientes del taller."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Cliente)

    async def buscar_por_documento(self, documento: str) -> Cliente | None:
        """Devuelve la ficha con ese documento, o ``None`` si no existe.

        El documento es único, así que la consulta devuelve a lo sumo una fila.
        """
        return await self._primero(
            self._sentencia().where(Cliente.documento == documento)
        )

    async def buscar_por_usuario(self, usuario_id: int) -> Cliente | None:
        """Devuelve la ficha vinculada a esa cuenta, o ``None`` si no tiene."""
        return await self._primero(
            self._sentencia().where(Cliente.usuario_id == usuario_id)
        )


class VehiculoRepository(SoftDeleteRepository[Vehiculo]):
    """Vehículos de los clientes, con baja lógica y patente vigente única."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Vehiculo)

    async def listar_vigentes_por_cliente(self, cliente_id: int) -> list[Vehiculo]:
        """Lista los vehículos vigentes del cliente, ordenados por patente.

        El orden estable por patente hace que la consulta de la ficha con sus
        vehículos sea reproducible entre peticiones.
        """
        sentencia = (
            self._sentencia()
            .where(
                self._no_borrados(),
                Vehiculo.cliente_id == cliente_id,
            )
            .order_by(Vehiculo.patente)
        )
        resultado = await self._session.scalars(sentencia)
        return [vehiculo for vehiculo in resultado.all()]

    async def buscar_vigente_por_patente(self, patente: str) -> Vehiculo | None:
        """Devuelve el vehículo vigente con esa patente, o ``None``.

        Un vehículo dado de baja libera su patente: la búsqueda sólo considera
        las filas sin marca de baja, igual que el índice único parcial.
        """
        return await self._primero(
            self._sentencia().where(
                self._no_borrados(),
                Vehiculo.patente == patente,
            )
        )
