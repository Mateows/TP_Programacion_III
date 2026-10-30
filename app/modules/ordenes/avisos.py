"""Aviso simulado al cliente cuando una orden se termina.

No hay canal real de notificación en el alcance de C-07: la terminación agenda
esta corrutina con ``BackgroundTasks`` después de que la unidad de trabajo
confirmó. La simulación coincide con SU-01 de la knowledge-base: espera ``0.5``
segundos y deja el mensaje en el registro del módulo. No toca la base ni hace
I/O de red. Una falla del proceso después de responder pierde el aviso, y eso
es aceptable porque no forma parte del contrato HTTP.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

__all__ = ["avisar_terminacion"]

ESPERA_SIMULADA = 0.5


async def avisar_terminacion(orden_id: int) -> None:
    """Simula el aviso de terminación: espera y registra el mensaje."""
    await asyncio.sleep(ESPERA_SIMULADA)
    logger.info(
        "Aviso simulado al cliente: la orden %s está terminada.",
        orden_id,
    )
