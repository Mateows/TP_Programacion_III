"""Servicio del módulo de repuestos.

El servicio no conoce HTTP: recibe la ``UnitOfWork`` que arma el router y, en
las escrituras, la cuenta actuante. Lanza errores de dominio de ``errors.py`` y
el router los traduce. Ninguna función confirma: la confirmación pertenece a la
unidad de trabajo.

El stock tiene un único punto de escritura por operación: el alta escribe su
stock inicial y su movimiento en la misma transacción, y la edición de precio
deja su línea de historial junto con el cambio del repuesto.
"""

from __future__ import annotations

from app.core.paginacion import (
    Pagina,
    PaginaFueraDeRango,
    ParametrosPagina,
    construir_pagina,
)
from app.core.repository import ConflictoDeIntegridad
from app.core.unit_of_work import UnitOfWork
from app.modules.repuestos.errors import (
    CodigoYaRegistrado,
    PrecioNoAumenta,
    RepuestoNoEncontrado,
)
from app.modules.repuestos.models import (
    HistorialPrecioRepuesto,
    MovimientoStock,
    Repuesto,
)
from app.modules.repuestos.motivos import MOTIVO_REPOSICION, MOTIVO_STOCK_INICIAL
from app.modules.repuestos.repository import (
    HistorialPrecioRepository,
    MovimientoStockRepository,
    RepuestoRepository,
)
from app.modules.repuestos.schemas import (
    AltaRepuestoRequest,
    EditarRepuestoRequest,
)
from app.modules.usuarios.models import Usuario

__all__ = [
    "consultar_movimientos",
    "consultar_precios",
    "crear_repuesto",
    "dar_de_baja_repuesto",
    "editar_repuesto",
    "listar_repuestos",
    "reponer_stock",
]


def _clave_primaria(entidad: Repuesto | Usuario) -> int:
    """Devuelve la clave ya asignada o falla si el ``flush`` no la generó."""
    if entidad.id is None:
        raise RuntimeError("La entidad no obtuvo su clave primaria al persistirse")
    return entidad.id


async def crear_repuesto(
    uow: UnitOfWork,
    datos: AltaRepuestoRequest,
    actor: Usuario,
) -> Repuesto:
    """Da de alta un repuesto y, si el stock inicial es positivo, su movimiento.

    Sólo el ``add`` del repuesto puede chocar con el índice único parcial del
    código: ese conflicto se traduce a ``CodigoYaRegistrado``. Cualquier
    conflicto posterior (por ejemplo, al insertar el movimiento) no es un código
    repetido y se propaga tal cual.

    Con ``stock == 0`` no se escribe movimiento porque el ``CHECK`` exige
    ``cantidad > 0``. El alta no escribe historial de precios: el precio
    inicial no es un cambio de precio.
    """
    async with uow:
        repuestos = RepuestoRepository(uow.session)
        movimientos = MovimientoStockRepository(uow.session)

        try:
            repuesto = await repuestos.add(
                Repuesto(
                    codigo=datos.codigo,
                    descripcion=datos.descripcion,
                    precio=datos.precio,
                    stock=datos.stock,
                )
            )
        except ConflictoDeIntegridad as error:
            raise CodigoYaRegistrado() from error

        if datos.stock > 0:
            await movimientos.add(
                MovimientoStock(
                    repuesto_id=_clave_primaria(repuesto),
                    usuario_id=_clave_primaria(actor),
                    cantidad=datos.stock,
                    motivo=MOTIVO_STOCK_INICIAL,
                    orden_id=None,
                )
            )

    _clave_primaria(repuesto)
    return repuesto


async def listar_repuestos(
    uow: UnitOfWork,
    parametros: ParametrosPagina,
    texto: str | None = None,
) -> Pagina[Repuesto]:
    """Devuelve una página del catálogo vigente, ordenada por descripción.

    Son dos consultas: primero el total, sin el cual no se puede saber si la
    página pedida existe, y después la página pedida. Ambas aplican el mismo
    filtro de búsqueda: ``total`` y ``pages`` describen sólo los repuestos que
    coinciden con ``texto``. Traer una página inexistente sólo para descartarla
    costaría una consulta de más.

    Un catálogo vacío tiene ``pages == 0``; la página 1 sigue siendo válida y
    devuelve una lista vacía. La página 2 ya no existe y se rechaza.
    """
    async with uow:
        repuestos = RepuestoRepository(uow.session)
        total = await repuestos.contar(texto=texto)

        previa = construir_pagina([], total, parametros)
        # Un catálogo vacío informa ``pages == 0``, pero su primera página
        # sigue siendo válida: sólo la página 2 en adelante no existe.
        ultima_pagina = max(previa.pages, 1)
        if parametros.page > ultima_pagina:
            raise PaginaFueraDeRango(parametros.page, previa.pages)

        filas = await repuestos.listar_paginado(
            texto=texto,
            limit=parametros.size,
            offset=parametros.offset,
        )

    return construir_pagina(filas, total, parametros)


async def editar_repuesto(
    uow: UnitOfWork,
    repuesto_id: int,
    datos: EditarRepuestoRequest,
    actor: Usuario,
) -> Repuesto:
    """Actualiza sólo los campos enviados de un repuesto vigente.

    ``get`` excluye los repuestos dados de baja, así que un identificador
    inexistente y uno ya dado de baja producen el mismo ``RepuestoNoEncontrado``.

    El precio sólo aumenta: uno menor se rechaza antes de escribir (sin mutar la
    entidad ni dejar historial), uno igual no escribe historial y uno mayor
    actualiza el repuesto y agrega la línea con el valor anterior, el nuevo y la
    cuenta actuante, dentro de la misma transacción. El ``flush`` final deja la
    fila persistida antes del ``commit`` de la unidad de trabajo.
    """
    async with uow:
        repuestos = RepuestoRepository(uow.session)
        historial = HistorialPrecioRepository(uow.session)

        repuesto = await repuestos.get(repuesto_id)
        if repuesto is None:
            raise RepuestoNoEncontrado()

        cambios = datos.model_dump(exclude_unset=True)

        descripcion = cambios.get("descripcion")
        if descripcion is not None:
            repuesto.descripcion = descripcion

        nuevo = cambios.get("precio")
        if nuevo is not None:
            if nuevo < repuesto.precio:
                raise PrecioNoAumenta()
            if nuevo > repuesto.precio:
                anterior = repuesto.precio
                repuesto.precio = nuevo
                await historial.add(
                    HistorialPrecioRepuesto(
                        repuesto_id=_clave_primaria(repuesto),
                        usuario_id=_clave_primaria(actor),
                        precio_anterior=anterior,
                        precio_nuevo=nuevo,
                    )
                )

        await repuestos.flush()

    _clave_primaria(repuesto)
    return repuesto


async def reponer_stock(
    uow: UnitOfWork,
    repuesto_id: int,
    cantidad: int,
    actor: Usuario,
) -> Repuesto:
    """Suma stock a un repuesto vigente y deja el movimiento de reposición.

    ``get`` excluye los repuestos dados de baja, así que un identificador
    inexistente y uno ya dado de baja producen el mismo ``RepuestoNoEncontrado``.
    La cantidad positiva la garantiza el contrato ``ReponerRequest``; el stock y
    el movimiento se escriben dentro de la misma transacción, y el ``flush``
    final deja ambas filas persistidas antes del ``commit`` de la unidad.
    """
    async with uow:
        repuestos = RepuestoRepository(uow.session)
        movimientos = MovimientoStockRepository(uow.session)

        repuesto = await repuestos.get(repuesto_id)
        if repuesto is None:
            raise RepuestoNoEncontrado()

        repuesto.stock += cantidad
        await movimientos.add(
            MovimientoStock(
                repuesto_id=_clave_primaria(repuesto),
                usuario_id=_clave_primaria(actor),
                cantidad=cantidad,
                motivo=MOTIVO_REPOSICION,
                orden_id=None,
            )
        )
        await repuestos.flush()

    _clave_primaria(repuesto)
    return repuesto


async def consultar_movimientos(
    uow: UnitOfWork,
    repuesto_id: int,
) -> list[MovimientoStock]:
    """Devuelve los movimientos del repuesto, del más reciente al más antiguo.

    Un repuesto inexistente o dado de baja responde igual que las escrituras:
    ``RepuestoNoEncontrado``. El orden lo resuelve el repositorio.
    """
    async with uow:
        repuestos = RepuestoRepository(uow.session)
        movimientos = MovimientoStockRepository(uow.session)

        if await repuestos.get(repuesto_id) is None:
            raise RepuestoNoEncontrado()

        return await movimientos.listar_por_repuesto(repuesto_id)


async def consultar_precios(
    uow: UnitOfWork,
    repuesto_id: int,
) -> list[HistorialPrecioRepuesto]:
    """Devuelve el historial de precios del repuesto, del más reciente al más antiguo.

    Un repuesto inexistente o dado de baja responde ``RepuestoNoEncontrado``,
    igual que el resto de las operaciones por identificador.
    """
    async with uow:
        repuestos = RepuestoRepository(uow.session)
        historial = HistorialPrecioRepository(uow.session)

        if await repuestos.get(repuesto_id) is None:
            raise RepuestoNoEncontrado()

        return await historial.listar_por_repuesto(repuesto_id)


async def dar_de_baja_repuesto(uow: UnitOfWork, repuesto_id: int) -> None:
    """Da de baja lógica un repuesto vigente, conservando su fila y su historial.

    ``get`` excluye las filas ya dadas de baja, así que una segunda baja
    responde ``RepuestoNoEncontrado`` sin escribir. ``soft_delete`` marca la fila
    y envía el cambio; la confirmación pertenece a la unidad de trabajo.
    """
    async with uow:
        repuestos = RepuestoRepository(uow.session)

        repuesto = await repuestos.get(repuesto_id)
        if repuesto is None:
            raise RepuestoNoEncontrado()

        await repuestos.soft_delete(repuesto)


