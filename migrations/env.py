import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, MetaData, pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from app.core.config import settings

# Importar los módulos de modelos registra sus tablas en ``SQLModel.metadata``.
# El import es por efecto secundario; el alias evita que el linter lo elimine.
from app.modules.clientes import models as _clientes_models  # noqa: F401
from app.modules.ordenes import models as _ordenes_models  # noqa: F401
from app.modules.repuestos import models as _repuestos_models  # noqa: F401
from app.modules.usuarios import models as _usuarios_models  # noqa: F401

# Objeto de configuración de Alembic (valores de alembic.ini).
config = context.config

# Configuración de logging de Alembic.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La metadata real proviene de los modelos SQLModel de todos los módulos de
# dominio, registrados por los imports anteriores. C-09 autogenera la
# migración 001 a partir de ella.
target_metadata: MetaData = SQLModel.metadata


def get_database_url() -> str:
    """URL async tomada de la configuración de la aplicación.

    No hay credenciales hardcodeadas: ``Settings`` lee el entorno o ``.env``
    y falla de forma explícita si falta una variable obligatoria.
    """
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Ejecuta las migraciones en modo 'offline' (sin conexión)."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Ejecuta las migraciones sobre una conexión ya establecida."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Ejecuta las migraciones en modo 'online' con un motor async."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
