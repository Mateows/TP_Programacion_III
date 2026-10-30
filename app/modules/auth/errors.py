"""Errores de dominio del módulo de autenticación.

El servicio no conoce HTTP: lanza estos errores y el router los traduce a los
estados ``401``, ``409``, ``422`` y ``429`` con sus cabeceras. Así el servicio
se prueba sin ``TestClient`` y la traducción queda en un solo lugar.
"""

MENSAJE_CREDENCIALES_INVALIDAS = "Credenciales inválidas"


class ErrorAutenticacion(Exception):
    """Base de los errores de dominio de autenticación."""


class CredencialesInvalidas(ErrorAutenticacion):
    """Correo inexistente, contraseña incorrecta o cuenta inactiva.

    Siempre el mismo mensaje y el mismo estado: la respuesta no debe revelar
    si la cuenta existe ni si está activa.
    """

    def __init__(self, mensaje: str = MENSAJE_CREDENCIALES_INVALIDAS) -> None:
        super().__init__(mensaje)


class LimiteDeIntentosExcedido(ErrorAutenticacion):
    """Demasiados fallos recientes para ese correo y dirección.

    ``retry_after`` son los segundos que faltan para que el fallo más antiguo
    que todavía cuenta salga de la ventana; el router lo publica en
    ``Retry-After``.
    """

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Demasiados intentos fallidos. Reintentá en {retry_after} segundos"
        )


class PasswordInvalida(ErrorAutenticacion):
    """La contraseña no cumple el límite de 1 a 72 bytes UTF-8.

    El schema de entrada ya lo valida; el servicio vuelve a sostener la regla
    porque bcrypt ignora en silencio lo que excede los 72 bytes.
    """


class CorreoYaRegistrado(ErrorAutenticacion):
    """Ya existe una cuenta con ese correo."""

    def __init__(self, mensaje: str = "El correo ya está registrado") -> None:
        super().__init__(mensaje)
