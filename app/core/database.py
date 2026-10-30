from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

SessionFactory = async_sessionmaker[AsyncSession]


def create_engine_and_session_factory() -> tuple[AsyncEngine, SessionFactory]:
    """Crea el motor async y la fábrica de sesiones.

    Debe llamarse desde el lifespan de la aplicación: no crea recursos
    al importar el módulo. El motor queda a cargo de quien lo crea, que
    debe liberarlo con ``await engine.dispose()`` al apagar la app.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.SQL_ECHO,
        pool_pre_ping=True,
    )

    session_factory: SessionFactory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return engine, session_factory


def get_engine(request: Request) -> AsyncEngine:
    """Devuelve el motor async guardado en ``app.state``.

    Falla de forma explícita si el lifespan no inicializó el motor.
    """
    engine: AsyncEngine | None = getattr(request.app.state, "engine", None)
    if engine is None:
        raise RuntimeError(
            "El motor de base de datos no está inicializado en app.state. "
            "Verificá que el lifespan de la aplicación se haya ejecutado."
        )
    return engine


def get_session_factory(request: Request) -> SessionFactory:
    """Devuelve la fábrica de sesiones guardada en ``app.state``.

    Falla de forma explícita si el lifespan no inicializó la fábrica.
    """
    session_factory: SessionFactory | None = getattr(
        request.app.state, "session_factory", None
    )
    if session_factory is None:
        raise RuntimeError(
            "La fábrica de sesiones no está inicializada en app.state. "
            "Verificá que el lifespan de la aplicación se haya ejecutado."
        )
    return session_factory


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Entrega una sesión asíncrona desde la fábrica guardada en ``app.state``.

    La sesión se cierra automáticamente al terminar la petición (``yield``).
    """
    session_factory = get_session_factory(request)
    async with session_factory() as session:
        yield session
