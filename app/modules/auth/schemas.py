"""Contratos de entrada y salida del módulo de autenticación.

Todos los schemas usan Pydantic V2 con ``extra="forbid"``: un campo que el
contrato no declara es un error de validación, no un dato ignorado. Las
contraseñas se miden en bytes UTF-8 (1 a 72) porque bcrypt ignora en silencio
lo que excede los 72 bytes.

Ningún schema de respuesta declara un campo de token: el token viaja
únicamente en la cookie ``access_token`` (HttpOnly).
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

# bcrypt solo considera los primeros 72 bytes de la contraseña: se rechaza
# cualquier valor fuera de ese rango en lugar de truncarlo en silencio.
MIN_PASSWORD_BYTES = 1
MAX_PASSWORD_BYTES = 72

# Nombres de campo de contraseña que valida el mixin. ``check_fields=False``
# permite que cada schema declare solo los que necesita.
CAMPOS_PASSWORD: tuple[str, ...] = ("password", "password_actual", "password_nueva")


def validar_password(valor: str) -> str:
    """Exige que la contraseña ocupe entre 1 y 72 bytes en UTF-8."""
    tamano = len(valor.encode("utf-8"))
    if tamano < MIN_PASSWORD_BYTES:
        raise ValueError(
            f"La contraseña debe ocupar al menos {MIN_PASSWORD_BYTES} byte en UTF-8"
        )
    if tamano > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"La contraseña no puede superar los {MAX_PASSWORD_BYTES} bytes en UTF-8"
        )
    return valor


class PasswordValidadaMixin:
    """Aplica el límite de bytes a todo campo de contraseña declarado.

    El validador se comparte entre registro, login y cambio de contraseña
    para que el límite no dependa de cada schema.
    """

    @field_validator(*CAMPOS_PASSWORD, check_fields=False)
    @classmethod
    def _validar_password(cls, valor: str) -> str:
        return validar_password(valor)


class RegistroRequest(PasswordValidadaMixin, BaseModel):
    """Datos del alta de una cuenta de cliente.

    ``documento`` identifica la ficha del taller (RN-02) y es obligatorio: sin
    él la cuenta no puede tener vehículos. Se persiste tal como llega; la
    normalización no forma parte del contrato de registro. ``telefono`` es
    opcional y puede quedar nulo en la ficha.
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=255)
    nombre: str = Field(max_length=150)
    documento: str = Field(max_length=50)
    telefono: str | None = Field(default=None, max_length=30)
    password: str


class LoginRequest(PasswordValidadaMixin, BaseModel):
    """Credenciales declaradas al iniciar sesión."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=255)
    password: str


class CambioPasswordRequest(PasswordValidadaMixin, BaseModel):
    """Contraseña actual y su reemplazo, en un cambio autenticado."""

    model_config = ConfigDict(extra="forbid")

    password_actual: str
    password_nueva: str


class SesionResponse(BaseModel):
    """Cuenta autenticada con sus roles vigentes y los roles del token.

    ``roles_vigentes`` son los que autorizan (consulta a la base);
    ``roles_token`` son informativos y reflejan lo emitido al iniciar sesión.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool
    roles_vigentes: list[str]
    roles_token: list[str]


class MensajeSesionResponse(BaseModel):
    """Resultado de un login o cambio de contraseña, sin el token."""

    model_config = ConfigDict(extra="forbid")

    mensaje: str
    debe_cambiar_password: bool
    expira_en_segundos: int


class MensajeResponse(BaseModel):
    """Resultado de una operación que no devuelve datos de sesión."""

    model_config = ConfigDict(extra="forbid")

    mensaje: str
