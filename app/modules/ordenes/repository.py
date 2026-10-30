"""Repositorios del módulo de órdenes de trabajo.

``EstadoOrdenRepository`` lee el catálogo de estados en el orden en que la API
los expone. ``OrdenTrabajoRepository`` resuelve el listado paginado con la
patente del vehículo y el detalle completo con un número fijo de consultas:
orden con vehículo, cliente y mecánico; ítems con su repuesto; e historial.
``ItemOrdenRepository`` e ``HistorialEstadoOrdenRepository`` sirven a esas
mismas lecturas por separado. Los modelos son planos, así que las relaciones
se resuelven con ``JOIN`` explícitos. Estos JOIN son la estrategia de carga
anticipada del módulo: evitan cargas perezosas o N+1. Ninguna consulta
confirma: la confirmación pertenece a la unidad de trabajo.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import (
    EstadoOrden,
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)
from app.modules.repuestos.models import Repuesto
from app.modules.usuarios.models import Usuario


@dataclass(frozen=True)
class FilaOrdenResumen:
    """Fila del listado: la orden y la patente de su vehículo."""

    orden: OrdenTrabajo
    patente: str


@dataclass(frozen=True)
class FilaItemOrden:
    """Ítem de una orden con el repuesto que referencia."""

    item: ItemOrden
    repuesto: Repuesto


@dataclass(frozen=True)
class DetalleOrdenFila:
    """Detalle de una orden con sus filas ya resueltas.

    El servicio recibe todo junto para no disparar consultas por ítem. El
    mecánico es nulo mientras la orden no tenga asignación.
    """

    orden: OrdenTrabajo
    vehiculo: Vehiculo
    cliente: Cliente
    mecanico: Usuario | None
    items: list[FilaItemOrden]
    historial: list[HistorialEstadoOrden]


class EstadoOrdenRepository(BaseRepository[EstadoOrden]):
    """Catálogo de estados del ciclo de vida, ordenado por posición."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EstadoOrden)

    async def listar(self) -> list[EstadoOrden]:
        """Lista los estados en el orden en que se presentan.

        ``posicion`` es único, pero se desempata por ``codigo`` para que el
        orden sea determinista aun si el catálogo tuviera duplicados.
        """
        sentencia = self._sentencia().order_by(
            EstadoOrden.posicion,
            EstadoOrden.codigo,
        )
        resultado = await self._session.scalars(sentencia)
        return [estado for estado in resultado.all()]

    async def existe(self, codigo: str) -> bool:
        """Indica si el catálogo declara ese código."""
        encontrado = await self._primero(
            self._sentencia().where(EstadoOrden.codigo == codigo)
        )
        return encontrado is not None


class OrdenTrabajoRepository(BaseRepository[OrdenTrabajo]):
    """Órdenes de trabajo, sin baja lógica: se cancelan, no se borran."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrdenTrabajo)

    async def contar(
        self,
        *filtros: Any,
        estado: str | None = None,
    ) -> int:
        """Cuenta las órdenes que cumplen los filtros y el estado indicado.

        El filtro de estado es opcional y se combina con los filtros libres
        para que el total describa exactamente el conjunto listado.
        """
        if estado is not None:
            filtros = (OrdenTrabajo.estado == estado, *filtros)
        return await super().contar(*filtros)

    async def listar_paginado(
        self,
        *,
        estado: str | None,
        limit: int,
        offset: int,
    ) -> list[FilaOrdenResumen]:
        """Lista una página de órdenes con la patente de su vehículo.

        El orden por creación e identificador descendente es estable, de modo
        que las páginas no se solapan. El estado viaja como parámetro ligado.
        """
        sentencia: Select[Any] = (
            select(OrdenTrabajo, Vehiculo.patente)
            .select_from(OrdenTrabajo)
            .join(Vehiculo, OrdenTrabajo.vehiculo_id == Vehiculo.id)
        )
        if estado is not None:
            sentencia = sentencia.where(OrdenTrabajo.estado == estado)
        sentencia = (
            sentencia.order_by(
                OrdenTrabajo.creada_en.desc(),
                OrdenTrabajo.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        resultado = await self._session.execute(sentencia)
        return [
            FilaOrdenResumen(orden=fila[0], patente=fila[1])
            for fila in resultado.all()
        ]

    async def contar_por_cliente(self, cliente_id: int) -> int:
        """Cuenta las órdenes cuyos vehículos pertenecen a la ficha indicada."""
        sentencia = (
            select(func.count())
            .select_from(OrdenTrabajo)
            .join(Vehiculo, OrdenTrabajo.vehiculo_id == Vehiculo.id)
            .where(Vehiculo.cliente_id == cliente_id)
        )
        resultado = await self._session.scalars(sentencia)
        return int(resultado.first() or 0)

    async def listar_paginado_por_cliente(
        self,
        *,
        cliente_id: int,
        limit: int,
        offset: int,
    ) -> list[FilaOrdenResumen]:
        """Lista órdenes propias, incluyendo vehículos dados de baja.

        El filtro usa la relación histórica ``vehiculo.cliente_id`` y no
        ``borrado_en``: dar de baja un vehículo no debe ocultar sus órdenes.
        """
        sentencia: Select[Any] = (
            select(OrdenTrabajo, Vehiculo.patente)
            .select_from(OrdenTrabajo)
            .join(Vehiculo, OrdenTrabajo.vehiculo_id == Vehiculo.id)
            .where(Vehiculo.cliente_id == cliente_id)
            .order_by(
                OrdenTrabajo.creada_en.desc(),
                OrdenTrabajo.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        resultado = await self._session.execute(sentencia)
        return [
            FilaOrdenResumen(orden=fila[0], patente=fila[1])
            for fila in resultado.all()
        ]

    async def listar_detalle(self, orden_id: int) -> DetalleOrdenFila | None:
        """Arma el detalle de la orden con un número fijo de consultas.

        Son exactamente tres: la orden con vehículo, cliente y mecánico; sus
        ítems con el repuesto; y su historial en orden cronológico. No hay
        cargas perezosas ni consultas por ítem.
        """
        resultado_orden = await self._session.execute(
            select(OrdenTrabajo, Vehiculo, Cliente, Usuario)
            .select_from(OrdenTrabajo)
            .join(Vehiculo, OrdenTrabajo.vehiculo_id == Vehiculo.id)
            .join(Cliente, Vehiculo.cliente_id == Cliente.id)
            .outerjoin(Usuario, OrdenTrabajo.mecanico_id == Usuario.id)
            .where(OrdenTrabajo.id == orden_id)
        )
        fila_orden = resultado_orden.first()
        if fila_orden is None:
            return None
        fila_orden_trabajo, fila_vehiculo, fila_cliente, fila_mecanico = fila_orden

        resultado_items = await self._session.execute(
            select(ItemOrden, Repuesto)
            .select_from(ItemOrden)
            .join(Repuesto, ItemOrden.repuesto_id == Repuesto.id)
            .where(ItemOrden.orden_id == orden_id)
            .order_by(ItemOrden.id)
        )
        items = [
            FilaItemOrden(item=fila[0], repuesto=fila[1])
            for fila in resultado_items.all()
        ]

        resultado_historial = await self._session.execute(
            select(HistorialEstadoOrden)
            .where(HistorialEstadoOrden.orden_id == orden_id)
            .order_by(
                HistorialEstadoOrden.cuando,
                HistorialEstadoOrden.id,
            )
        )
        historial = list(resultado_historial.scalars().all())

        return DetalleOrdenFila(
            orden=fila_orden_trabajo,
            vehiculo=fila_vehiculo,
            cliente=fila_cliente,
            mecanico=fila_mecanico,
            items=items,
            historial=historial,
        )


class ItemOrdenRepository(BaseRepository[ItemOrden]):
    """Ítems de una orden con el repuesto que cada uno referencia."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ItemOrden)

    async def listar_por_orden(self, orden_id: int) -> list[FilaItemOrden]:
        """Lista los ítems de la orden con su repuesto, por identificador."""
        sentencia = (
            select(ItemOrden, Repuesto)
            .select_from(ItemOrden)
            .join(Repuesto, ItemOrden.repuesto_id == Repuesto.id)
            .where(ItemOrden.orden_id == orden_id)
            .order_by(ItemOrden.id)
        )
        resultado = await self._session.execute(sentencia)
        return [
            FilaItemOrden(item=fila[0], repuesto=fila[1])
            for fila in resultado.all()
        ]


class HistorialEstadoOrdenRepository(BaseRepository[HistorialEstadoOrden]):
    """Historial de estados de una orden, de sólo agregado."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HistorialEstadoOrden)

    async def listar_por_orden(
        self,
        orden_id: int,
    ) -> list[HistorialEstadoOrden]:
        """Lista las transiciones de la orden en orden cronológico."""
        sentencia = (
            self._sentencia()
            .where(HistorialEstadoOrden.orden_id == orden_id)
            .order_by(
                HistorialEstadoOrden.cuando,
                HistorialEstadoOrden.id,
            )
        )
        resultado = await self._session.scalars(sentencia)
        return [linea for linea in resultado.all()]
