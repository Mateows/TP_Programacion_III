"""Repositorios del módulo de repuestos.

``RepuestoRepository`` hereda el borrado lógico: sus lecturas excluyen las filas
dadas de baja y sobrescribe ``contar`` para que el total de la paginación
tampoco las cuente. ``MovimientoStockRepository`` e ``HistorialPrecioRepository``
sirven a las tablas de sólo agregado y devuelven sus filas de la más reciente a
la más antigua. Ninguna consulta confirma: la confirmación pertenece a la unidad
de trabajo.
"""

from typing import Any

from sqlalchemy import ColumnElement, Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.repuestos.models import (
    HistorialPrecioRepuesto,
    MovimientoStock,
    Repuesto,
)


def _filtro_descripcion(texto: str | None) -> ColumnElement[bool] | None:
    """Filtro de búsqueda por descripción, compartido por filas y conteo.

    Un único punto de construcción evita que el listado y el total apliquen
    patrones distintos y que ``pages`` describa un conjunto que el usuario no
    ve. El patrón viaja como parámetro ligado.
    """
    if not texto:
        return None
    return Repuesto.descripcion.ilike(f"%{texto}%")


class RepuestoRepository(SoftDeleteRepository[Repuesto]):
    """Catálogo de repuestos con baja lógica y código vigente único."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Repuesto)

    async def buscar_vigente_por_codigo(self, codigo: str) -> Repuesto | None:
        """Devuelve el repuesto vigente con ese código, o ``None``.

        Un repuesto dado de baja libera su código: la búsqueda sólo considera
        las filas sin marca de baja, igual que el índice único parcial.
        """
        return await self._primero(
            self._sentencia().where(
                self._no_borrados(),
                Repuesto.codigo == codigo,
            )
        )

    async def listar_paginado(
        self,
        *,
        texto: str | None,
        limit: int,
        offset: int,
    ) -> list[Repuesto]:
        """Lista una página de repuestos vigentes, ordenada por descripción e id.

        ``texto`` filtra por descripción sin distinguir mayúsculas y viaja como
        parámetro ligado. El orden estable hace que las páginas no se solapen.
        """
        sentencia: Select[Any] = self._sentencia().where(self._no_borrados())
        filtro = _filtro_descripcion(texto)
        if filtro is not None:
            sentencia = sentencia.where(filtro)
        sentencia = (
            sentencia.order_by(Repuesto.descripcion, Repuesto.id)
            .limit(limit)
            .offset(offset)
        )
        resultado = await self._session.scalars(sentencia)
        return [repuesto for repuesto in resultado.all()]

    async def contar(
        self,
        *filtros: Any,
        texto: str | None = None,
    ) -> int:
        """Cuenta los repuestos vigentes que cumplen los filtros indicados.

        ``texto`` aplica la misma búsqueda por descripción que
        ``listar_paginado``, para que ``total`` y ``pages`` describan
        exactamente el conjunto listado.
        """
        filtro = _filtro_descripcion(texto)
        if filtro is not None:
            filtros = (filtro, *filtros)
        return await super().contar(self._no_borrados(), *filtros)

    async def listar_vigentes_por_ids(self, ids: list[int]) -> list[Repuesto]:
        """Lista los repuestos vigentes con esos identificadores, en una consulta.

        Resuelve el alta de una orden sin una consulta por ítem. Un repuesto
        inexistente o dado de baja simplemente no aparece en el resultado. Sin
        identificadores no hay nada que buscar, así que no se consulta.
        """
        if not ids:
            return []
        sentencia = (
            self._sentencia()
            .where(self._no_borrados(), Repuesto.id.in_(ids))
            .order_by(Repuesto.id)
        )
        resultado = await self._session.scalars(sentencia)
        return [repuesto for repuesto in resultado.all()]

    async def listar_por_ids_para_actualizar(
        self,
        ids: list[int],
    ) -> list[Repuesto]:
        """Lista y bloquea los repuestos vigentes con esos identificadores.

        ``SELECT ... FOR UPDATE`` serializa la lectura del stock con la
        escritura de la terminación de una orden (C-07): la validación de
        ``stock >= cantidad`` y el descuento no pueden intercalarse con otra
        transacción que consuma el mismo repuesto. Sin identificadores no hay
        nada que bloquear, así que no se consulta.
        """
        if not ids:
            return []
        sentencia = (
            self._sentencia()
            .where(self._no_borrados(), Repuesto.id.in_(ids))
            .order_by(Repuesto.id)
            .with_for_update()
        )
        resultado = await self._session.scalars(sentencia)
        return [repuesto for repuesto in resultado.all()]


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    """Movimientos de stock de sólo agregado, del más reciente al más antiguo."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MovimientoStock)

    async def listar_por_repuesto(self, repuesto_id: int) -> list[MovimientoStock]:
        """Lista los movimientos del repuesto, del más reciente al más antiguo."""
        sentencia = (
            self._sentencia()
            .where(MovimientoStock.repuesto_id == repuesto_id)
            .order_by(MovimientoStock.cuando.desc(), MovimientoStock.id.desc())
        )
        resultado = await self._session.scalars(sentencia)
        return [movimiento for movimiento in resultado.all()]


class HistorialPrecioRepository(BaseRepository[HistorialPrecioRepuesto]):
    """Historial de precios de sólo agregado, del más reciente al más antiguo."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HistorialPrecioRepuesto)

    async def listar_por_repuesto(
        self,
        repuesto_id: int,
    ) -> list[HistorialPrecioRepuesto]:
        """Lista los cambios de precio del repuesto, del más reciente al más antiguo."""
        sentencia = (
            self._sentencia()
            .where(HistorialPrecioRepuesto.repuesto_id == repuesto_id)
            .order_by(
                HistorialPrecioRepuesto.cuando.desc(),
                HistorialPrecioRepuesto.id.desc(),
            )
        )
        resultado = await self._session.scalars(sentencia)
        return [linea for linea in resultado.all()]
