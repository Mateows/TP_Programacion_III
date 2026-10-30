"""Sondas de salud del sistema (liveness y readiness).

``GET /health/live`` confirma que el proceso está en pie y no toca la base.
``GET /health/ready`` ejecuta ``SELECT 1`` en una sesión asíncrona para
confirmar la conectividad con PostgreSQL.

Contrato de respuestas:

- ``live``: ``200`` con ``{"status": "ok"}``.
- ``ready``: ``200`` con ``{"status": "ready"}`` si la base contesta, o ``503``
  con un detalle genérico si la conexión falla. El mensaje de la excepción
  original no se propaga: puede contener credenciales o datos internos.

Las dos rutas son públicas y viven en ``router_abierto``: una sonda de
infraestructura no puede depender de una cookie de sesión ni del cambio
obligatorio de contraseña.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

router = APIRouter(prefix="/health", tags=["Salud"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Mensaje público del 503: sin host, usuario ni mensaje del motor.
MENSAJE_BASE_NO_DISPONIBLE = "La base de datos no está disponible"


@router.get("/live")
async def live() -> dict[str, str]:
    """Confirma que la aplicación está en ejecución.

    No inyecta sesión ni consulta la base: sirve como liveness probe para
    detectar un proceso caído, no para validar dependencias externas.
    """
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    """Confirma que la base de datos responde.

    Ejecuta ``SELECT 1`` en la sesión de la petición. Cualquier excepción se
    traduce a ``503`` con un detalle genérico, sin filtrar el error original.
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=MENSAJE_BASE_NO_DISPONIBLE,
        ) from None
    return {"status": "ready"}
