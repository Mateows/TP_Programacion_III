"""Unidad de trabajo: frontera transaccional de cada operación de escritura.

La unidad de trabajo agrupa las escrituras de un bloque en una sola
transacción: confirma al salir sin excepciones, revierte ante cualquier
excepción y propaga el error. No abre transacción explícita (la primera
operación la inicia) y solo cierra la sesión cuando la creó ella.
"""

from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import traducir_integridad


class UnitOfWork:
    """Gestor de contexto async que confirma o revierte una sesión."""

    def __init__(self, session: AsyncSession, *, owns_session: bool = False) -> None:
        self._session = session
        self._owns_session = owns_session

    @property
    def session(self) -> AsyncSession:
        """Sesión sobre la que trabaja la unidad."""
        return self._session

    @property
    def owns_session(self) -> bool:
        """Indica si la unidad creó la sesión y debe liberarla al salir."""
        return self._owns_session

    async def __aenter__(self) -> "UnitOfWork":
        """Entrega la unidad ya lista; no abre transacción explícita."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Confirma el bloque o lo revierte si hubo una excepción.

        Devuelve ``False`` para que la excepción original siga su curso.
        Solo libera la sesión cuando la unidad la creó.
        """
        try:
            if exc_type is not None:
                await self._session.rollback()
                return False

            with traducir_integridad("commit"):
                try:
                    await self._session.commit()
                except IntegrityError:
                    await self._session.rollback()
                    raise

            return False
        finally:
            if self._owns_session:
                await self._session.close()
