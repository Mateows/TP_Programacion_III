"""Contratos de persistencia compartidos por los módulos de la aplicación.

El repositorio base envía los cambios pendientes con ``flush()`` y nunca
confirma: la confirmación es responsabilidad exclusiva de la unidad de
trabajo. Toda lectura se arma con ``select()`` de SQLAlchemy 2.0 y aplica
las opciones de carga anticipada que declara cada repositorio concreto.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Generic, Protocol, TypeVar, cast

from sqlalchemy import Column, ColumnElement, DateTime, Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

T = TypeVar("T", bound=SQLModel)

logger = logging.getLogger(__name__)

MENSAJE_CONFLICTO = "Los datos enviados entran en conflicto con información existente."


class ConflictoDeIntegridad(Exception):
    """Conflicto de integridad de datos, sin detalles del esquema.

    Reemplaza al ``IntegrityError`` del motor en la frontera de persistencia:
    quien invoca recibe un error de dominio identificable y nunca nombres de
    tablas, columnas, restricciones ni sentencias.
    """


@contextmanager
def traducir_integridad(operacion: str) -> Iterator[None]:
    """Traduce ``IntegrityError`` a ``ConflictoDeIntegridad``.

    El detalle original se registra solamente en el log; el mensaje que
    recibe quien invoca es genérico.
    """
    try:
        yield
    except IntegrityError as error:
        logger.warning(
            "Conflicto de integridad durante %s: %s",
            operacion,
            error,
            exc_info=True,
        )
        raise ConflictoDeIntegridad(MENSAJE_CONFLICTO) from None


class _EntidadConBorrado(Protocol):
    """Contrato mínimo que asume el repositorio con borrado lógico."""

    borrado_en: datetime | None


class TimestampMixin(SQLModel):
    """Marcas temporales de creación y última actualización.

    Ambas columnas son ``timestamptz`` y no nulas. El valor lo resuelve la
    base de datos con ``now()`` para no depender del reloj del proceso; la
    actualización la dispara ``onupdate`` en cada ``UPDATE``.
    """

    creado_en: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )
    actualizado_en: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )


class BaseRepository(Generic[T]):
    """Repositorio genérico de lectura y alta para una entidad de SQLModel.

    Recibe la sesión desde afuera (la unidad de trabajo la administra) y el
    tipo de modelo. Las lecturas aplican ``_load_options``, la tupla de
    opciones de carga anticipada que declara cada repositorio concreto.
    """

    _load_options: tuple[Any, ...] = ()

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    @property
    def session(self) -> AsyncSession:
        """Sesión compartida que administra la unidad de trabajo."""
        return self._session

    @property
    def model(self) -> type[T]:
        """Modelo de tabla que atiende este repositorio."""
        return self._model

    def _clave_primaria(self) -> Column[Any]:
        """Columna que hace de clave primaria del modelo."""
        tabla = cast(Any, self._model).__table__
        return next(iter(tabla.primary_key.columns))

    def _sentencia(self) -> Select[Any]:
        """Sentencia base del modelo con sus opciones de carga anticipada."""
        return select(self._model).options(*self._load_options)

    def _con_filtros(
        self,
        sentencia: Select[Any],
        filtros: tuple[Any, ...],
    ) -> Select[Any]:
        """Aplica los filtros indicados a una sentencia base."""
        if filtros:
            return sentencia.where(*filtros)
        return sentencia

    async def _primero(self, sentencia: Select[Any]) -> T | None:
        """Ejecuta la sentencia y devuelve la primera fila, o ``None``."""
        resultado = await self._session.scalars(sentencia)
        return resultado.first()

    async def get(self, id: Any) -> T | None:
        """Devuelve la entidad con esa clave primaria, o ``None``."""
        return await self._primero(
            self._sentencia().where(self._clave_primaria() == id)
        )

    async def list(
        self,
        *filtros: Any,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Lista entidades que cumplen los filtros, con paginación opcional."""
        sentencia = self._con_filtros(self._sentencia(), filtros)
        if limit is not None:
            sentencia = sentencia.limit(limit)
        if offset is not None:
            sentencia = sentencia.offset(offset)
        resultado = await self._session.scalars(sentencia)
        return [entidad for entidad in resultado.all()]

    async def contar(self, *filtros: Any) -> int:
        """Cuenta las filas que cumplen los filtros, sin carga anticipada.

        ``_sentencia()`` incluye las opciones de carga del repositorio
        concreto; un conteo no las necesita y un ``JOIN`` de carga alteraría
        el total. Los filtros se aplican con el mismo mecanismo que ``list``.
        """
        sentencia = self._con_filtros(
            select(func.count()).select_from(self._model),
            filtros,
        )
        resultado = await self._session.scalars(sentencia)
        return int(resultado.first() or 0)

    async def add(self, entidad: T) -> T:
        """Agrega la entidad a la sesión y envía los cambios pendientes."""
        self._session.add(entidad)
        await self.flush()
        return entidad

    async def flush(self) -> None:
        """Envía los cambios pendientes sin confirmarlos.

        Un rechazo de integridad del motor se traduce a
        ``ConflictoDeIntegridad``: el detalle del esquema solo va al log.
        """
        with traducir_integridad("flush"):
            await self._session.flush()


class SoftDeleteRepository(BaseRepository[T]):
    """Repositorio con borrado lógico sobre una columna ``borrado_en``.

    Las lecturas habituales excluyen las filas dadas de baja. La baja se
    marca con la fecha del momento y la fila se conserva: este repositorio
    no borra físicamente.
    """

    def _columna_borrado(self) -> Column[Any]:
        """Columna nullable que marca la baja lógica."""
        tabla = cast(Any, self._model).__table__
        return tabla.c["borrado_en"]

    def _no_borrados(self) -> ColumnElement[bool]:
        """Condición que excluye las filas ya dadas de baja."""
        return self._columna_borrado().is_(None)

    async def get(self, id: Any) -> T | None:
        """Devuelve la entidad vigente con esa clave primaria, o ``None``."""
        return await self._primero(
            self._sentencia().where(
                self._no_borrados(),
                self._clave_primaria() == id,
            )
        )

    async def get_by_id_including_deleted(self, id: Any) -> T | None:
        """Devuelve la entidad aunque tenga marca de baja lógica."""
        return await self._primero(
            self._sentencia().where(self._clave_primaria() == id)
        )

    async def list(
        self,
        *filtros: Any,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Lista entidades vigentes que cumplen los filtros indicados."""
        return await super().list(
            self._no_borrados(),
            *filtros,
            limit=limit,
            offset=offset,
        )

    async def soft_delete(self, entidad: T) -> T:
        """Marca la baja de la entidad si todavía no estaba dada de baja."""
        borrable = cast(_EntidadConBorrado, entidad)
        if borrable.borrado_en is None:
            borrable.borrado_en = datetime.now(UTC)
        await self.flush()
        return entidad
