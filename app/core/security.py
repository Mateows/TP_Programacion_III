import asyncio
import secrets
import time
from datetime import datetime
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = settings.JWT_EXPIRES_MINUTES

# Limita cuántas operaciones bcrypt corren a la vez fuera del event loop.
_BCRYPT_SEMAPHORE = asyncio.Semaphore(5)

# Hash ficticio del login: se calcula una sola vez por proceso y de forma
# perezosa (no al importar), para que verificar un correo inexistente cueste
# lo mismo que verificar una cuenta real.
_hash_ficticio_cache: str | None = None
_hash_ficticio_lock = asyncio.Lock()

# Claims de un JWT: estructura heterogénea por definición.
JWTPayload = dict[str, Any]


def _hash_password_sync(password: str) -> str:
    """Calcula el hash bcrypt de forma bloqueante (se ejecuta en un hilo)."""
    hashed: bytes = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_COST),
    )
    return hashed.decode("utf-8")


def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """Verifica un hash bcrypt de forma bloqueante (se ejecuta en un hilo)."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


async def hash_password(password: str) -> str:
    """Hashea una contraseña con bcrypt fuera del bucle de eventos.

    ``bcrypt.hashpw`` es bloqueante: se ejecuta con ``asyncio.to_thread``
    bajo un semáforo para no bloquear el event loop ni saturar la CPU.
    Devuelve el hash como ``str`` (bcrypt lo entrega como ``bytes``).
    """
    async with _BCRYPT_SEMAPHORE:
        return await asyncio.to_thread(_hash_password_sync, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt fuera del bucle de eventos.

    ``bcrypt.checkpw`` es bloqueante: se ejecuta con ``asyncio.to_thread``
    bajo el mismo semáforo. Un hash con formato inválido se considera
    no coincidente (no se propaga un error 500).
    """
    async with _BCRYPT_SEMAPHORE:
        try:
            return await asyncio.to_thread(
                _verify_password_sync,
                plain_password,
                hashed_password,
            )
        except ValueError:
            return False


async def hash_ficticio() -> str:
    """Devuelve el hash ficticio del login, calculado una sola vez.

    El valor se calcula con ``BCRYPT_COST`` para que verificar una contraseña
    contra él cueste lo mismo que contra el hash de una cuenta real. El
    cálculo es perezoso (no ocurre al importar el módulo) y está serializado
    con un ``asyncio.Lock`` para que dos logins concurrentes no lo calculen
    dos veces.
    """
    global _hash_ficticio_cache
    if _hash_ficticio_cache is not None:
        return _hash_ficticio_cache

    async with _hash_ficticio_lock:
        if _hash_ficticio_cache is None:
            _hash_ficticio_cache = await hash_password(secrets.token_urlsafe(32))
        return _hash_ficticio_cache


def token_emitido_antes_del_cambio(
    payload: JWTPayload,
    password_cambiada_en: datetime | None,
) -> bool:
    """Indica si el token es anterior al último cambio de contraseña.

    Compara el ``iat`` del token con la marca del cambio sin truncar ninguno
    de los dos: el token emitido por el propio cambio de contraseña se fija
    con el mismo instante y queda válido. Acepta ``iat`` entero (tokens
    anteriores a C-03) o con fracción de segundo.

    Devuelve ``False`` cuando la cuenta nunca cambió su contraseña. Un
    payload sin ``iat`` utilizable se considera anterior al cambio, porque no
    se puede demostrar que sea posterior.
    """
    if password_cambiada_en is None:
        return False

    iat = payload.get("iat")
    if isinstance(iat, bool) or not isinstance(iat, (int, float)):
        return True

    return float(iat) < password_cambiada_en.timestamp()


def create_access_token(
    data: JWTPayload,
    expires_delta_minutes: int = JWT_EXPIRES_MINUTES,
    *,
    emitido_en: datetime | None = None,
) -> str:
    """Emite un JWT firmado con ``sub``, ``iat`` y ``exp``.

    El token viaja solamente en la cookie ``access_token`` (HttpOnly),
    nunca en el cuerpo de la respuesta ni en el header ``Authorization``.
    El vencimiento se calcula a partir de ``expires_delta_minutes``: el
    parámetro no se ignora.

    ``iat`` y ``exp`` se emiten con ``time.time()`` sin truncar: la fracción
    de segundo permite comparar el token con ``password_cambiada_en`` y
    aceptar el token emitido por el propio cambio de contraseña, aunque el
    cambio y la emisión caigan en el mismo segundo.

    ``emitido_en`` permite fijar el instante de emisión: el cambio de
    contraseña lo usa para emitir el token con el mismo reloj con el que
    escribió ``password_cambiada_en``, sin una segunda lectura que podría
    quedar por detrás.
    """
    now = emitido_en.timestamp() if emitido_en is not None else time.time()
    payload: JWTPayload = dict(data)
    payload["iat"] = now
    payload["exp"] = now + (expires_delta_minutes * 60)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> JWTPayload | None:
    """Decodifica y verifica un JWT (firma y ``exp``).

    Devuelve ``None`` si el token es inválido, está vencido o no se puede
    verificar con la clave configurada.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
