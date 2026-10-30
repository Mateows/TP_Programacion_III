"""Utilidades de la cookie de sesión.

El token viaja únicamente en la cookie ``access_token``: ``HttpOnly`` para que
el JavaScript de la página no lo lea, ``SameSite=Lax`` contra envíos cruzados,
``path="/"`` para toda la API y ``Secure`` cuando el despliegue usa TLS.

``Max-Age`` coincide siempre con la vigencia del token, y el cierre de sesión
la borra con ``Max-Age=0``.
"""

from fastapi import Response

from app.core.config import settings

NOMBRE_COOKIE = "access_token"


def fijar_cookie_sesion(response: Response, token: str) -> None:
    """Adjunta la cookie de sesión a la respuesta, sin exponer el token."""
    response.set_cookie(
        key=NOMBRE_COOKIE,
        value=token,
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        path="/",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )


def borrar_cookie_sesion(response: Response) -> None:
    """Marca la cookie de sesión para que el cliente la descarte.

    Conserva las mismas marcas con las que se creó: un navegador solo borra la
    cookie si coinciden nombre, ``path`` y dominio.
    """
    response.delete_cookie(
        key=NOMBRE_COOKIE,
        path="/",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
