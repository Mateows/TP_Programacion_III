from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación leída desde el entorno o ``.env``.

    Los secretos no tienen valor por defecto: si faltan, la aplicación falla
    al arrancar en lugar de usar credenciales inseguras.
    """

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    SECRET_KEY: str
    BCRYPT_COST: int = 12
    SQL_ECHO: bool = False
    # La cookie de sesión solo se marca ``Secure`` cuando se sirve por TLS.
    COOKIE_SECURE: bool = False
    JWT_EXPIRES_MINUTES: int = 30
    LOGIN_MAX_INTENTOS: int = 5
    LOGIN_VENTANA_SEGUNDOS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """URL de conexión async a PostgreSQL construida desde el entorno."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
