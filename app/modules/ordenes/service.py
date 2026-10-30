"""Servicio del módulo de órdenes de trabajo.

El servicio no conoce HTTP: recibe la ``UnitOfWork`` que arma el router y, en
las escrituras, la cuenta actuante. Lanza errores de dominio de ``errors.py``
y el router los traduce. Ninguna función confirma: la confirmación pertenece a
la unidad de trabajo.

El alta valida el catálogo, el vehículo y los repuestos antes de escribir y
congela el precio de cada ítem junto con el total. No mueve stock: el
inventario cambia recién al terminar la orden (RN-14). El listado valida el
estado contra el catálogo y reutiliza la convención de paginación de repuestos.

El detalle devuelve la orden ya resuelta a una cuenta de personal o al dueño
del vehículo: primero ``404`` si no existe y después ``403`` si no tiene
permiso. El catálogo de estados se expone en el orden de ``posicion`` y es de
sólo lectura.

Las transiciones siguen el mismo orden de errores (``404``, ``403`` y recién
después ``409``) y escriben estado, historial y, al terminar, el consumo de
stock dentro de una única unidad de trabajo. La terminación valida todos los
repuestos bloqueados antes de mutar y deja un movimiento positivo por ítem con
el motivo de consumo; el total no se recalcula porque el precio quedó
congelado.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.core.dependencies import UsuarioAutenticado
from app.core.paginacion import (
    Pagina,
    PaginaFueraDeRango,
    ParametrosPagina,
    construir_pagina,
)
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import (
    ClienteRepository,
    VehiculoRepository,
)
from app.modules.clientes.errors import SinFichaDeCliente
from app.modules.ordenes.errors import (
    CatalogoDeEstadosVacio,
    EstadoNoDeclarado,
    OrdenNoEncontrada,
    RepuestoNoDisponible,
    SinPermisoSobreLaOrden,
    StockInsuficiente,
    TransicionNoPermitida,
    VehiculoNoDisponible,
)
from app.modules.ordenes.models import (
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)
from app.modules.ordenes.repository import (
    EstadoOrdenRepository,
    ItemOrdenRepository,
    OrdenTrabajoRepository,
)
from app.modules.ordenes.schemas import (
    AltaOrdenRequest,
    EstadoOrdenResponse,
    OrdenDetalleResponse,
    OrdenResumenResponse,
    detalle_desde_fila,
    resumen_desde_fila,
)
from app.modules.repuestos.models import MovimientoStock
from app.modules.repuestos.motivos import MOTIVO_CONSUMO_ORDEN
from app.modules.repuestos.repository import (
    MovimientoStockRepository,
    RepuestoRepository,
)

__all__ = [
    "ESTADO_CANCELADA",
    "ESTADO_EN_REPARACION",
    "ESTADO_PENDIENTE",
    "ESTADO_TERMINADA",
    "ROLES_DE_PERSONAL",
    "cancelar_orden",
    "consultar_orden",
    "crear_orden",
    "iniciar_orden",
    "listar_estados",
    "listar_mis_ordenes",
    "listar_ordenes",
    "terminar_orden",
]

ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_EN_REPARACION = "EN_REPARACION"
ESTADO_TERMINADA = "TERMINADA"
ESTADO_CANCELADA = "CANCELADA"
CENTAVOS = Decimal("0.01")
ROLES_DE_PERSONAL = ("ADMIN", "RECEPCION", "MECANICO")


def _clave_primaria(entidad: OrdenTrabajo) -> int:
    """Devuelve la clave ya asignada o falla si el ``flush`` no la generó."""
    if entidad.id is None:
        raise RuntimeError("La entidad no obtuvo su clave primaria al persistirse")
    return entidad.id


def _id_del_actor(actor: UsuarioAutenticado) -> int:
    """Devuelve la clave de la cuenta autenticada.

    ``get_current_user`` carga la cuenta desde la base, así que su clave
    siempre existe; la comprobación explícita evita escribir un historial con
    un ``usuario_id`` nulo.
    """
    if actor.id is None:
        raise RuntimeError("La cuenta autenticada no tiene clave primaria")
    return actor.id


def _total_de(items: list[ItemOrden]) -> Decimal:
    """Suma cantidad por precio con ``Decimal`` y cuantiza a dos decimales."""
    total = sum(
        (item.precio_unitario * item.cantidad for item in items),
        Decimal("0.00"),
    )
    return total.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


async def crear_orden(
    uow: UnitOfWork,
    *,
    datos: AltaOrdenRequest,
    actor: UsuarioAutenticado,
) -> OrdenDetalleResponse:
    """Registra una orden ``PENDIENTE`` con sus ítems y su primera línea.

    El orden de las comprobaciones es el del diseño: catálogo con
    ``PENDIENTE``, vehículo vigente y repuestos vigentes en una sola consulta.
    Un rechazo no escribe nada y la unidad de trabajo revierte. Los precios se
    copian del repuesto y el total lo calcula el servidor; un ``precio`` o un
    ``total`` en el cuerpo ya fue rechazado por el contrato.
    """
    async with uow:
        estados = EstadoOrdenRepository(uow.session)
        if await estados.contar() == 0 or not await estados.existe(
            ESTADO_PENDIENTE
        ):
            raise CatalogoDeEstadosVacio()

        if await VehiculoRepository(uow.session).get(datos.vehiculo_id) is None:
            raise VehiculoNoDisponible()

        ids = [item.repuesto_id for item in datos.items]
        vigentes = await RepuestoRepository(
            uow.session
        ).listar_vigentes_por_ids(ids)
        por_id = {repuesto.id: repuesto for repuesto in vigentes}
        if any(repuesto_id not in por_id for repuesto_id in ids):
            raise RepuestoNoDisponible()

        items = [
            ItemOrden(
                repuesto_id=item.repuesto_id,
                cantidad=item.cantidad,
                precio_unitario=por_id[item.repuesto_id].precio,
            )
            for item in datos.items
        ]

        ordenes = OrdenTrabajoRepository(uow.session)
        orden = await ordenes.add(
            OrdenTrabajo(
                vehiculo_id=datos.vehiculo_id,
                estado=ESTADO_PENDIENTE,
                falla=datos.falla,
                total=_total_de(items),
            )
        )
        orden_id = _clave_primaria(orden)

        for item in items:
            item.orden_id = orden_id
            await ordenes.add(item)

        await ordenes.add(
            HistorialEstadoOrden(
                orden_id=orden_id,
                desde_estado=None,
                hasta_estado=ESTADO_PENDIENTE,
                usuario_id=_id_del_actor(actor),
            )
        )
        await ordenes.flush()

        fila = await ordenes.listar_detalle(orden_id)
        if fila is None:
            raise RuntimeError("La orden recién creada no se pudo leer")

    return detalle_desde_fila(fila)


async def listar_ordenes(
    uow: UnitOfWork,
    *,
    parametros: ParametrosPagina,
    estado: str | None,
) -> Pagina[OrdenResumenResponse]:
    """Devuelve una página de órdenes, con filtro opcional por estado.

    Si llega un estado, se valida contra el catálogo antes de contar: un código
    inexistente es ``EstadoNoDeclarado`` (``422``). El conteo y las filas
    aplican el mismo filtro, de modo que ``total`` y ``pages`` describen
    exactamente el conjunto listado.

    Se adopta la convención de repuestos: un listado vacío tiene ``pages == 0``
    y su página 1 sigue siendo válida; sólo la página 2 en adelante se rechaza.
    """
    async with uow:
        if estado is not None and not await EstadoOrdenRepository(
            uow.session
        ).existe(estado):
            raise EstadoNoDeclarado()

        ordenes = OrdenTrabajoRepository(uow.session)
        total = await ordenes.contar(estado=estado)

        previa = construir_pagina([], total, parametros)
        ultima_pagina = max(previa.pages, 1)
        if parametros.page > ultima_pagina:
            raise PaginaFueraDeRango(parametros.page, previa.pages)

        filas = await ordenes.listar_paginado(
            estado=estado,
            limit=parametros.size,
            offset=parametros.offset,
        )
        items = [resumen_desde_fila(fila) for fila in filas]

    return construir_pagina(items, total, parametros)


async def listar_mis_ordenes(
    uow: UnitOfWork,
    *,
    actor: UsuarioAutenticado,
    parametros: ParametrosPagina,
) -> Pagina[OrdenResumenResponse]:
    """Devuelve sólo las órdenes de los vehículos del cliente autenticado."""
    async with uow:
        usuario_id = actor.id
        if usuario_id is None:
            raise SinFichaDeCliente()

        cliente = await ClienteRepository(uow.session).buscar_por_usuario(
            usuario_id
        )
        if cliente is None or cliente.id is None:
            raise SinFichaDeCliente()

        ordenes = OrdenTrabajoRepository(uow.session)
        total = await ordenes.contar_por_cliente(cliente.id)
        previa = construir_pagina([], total, parametros)
        ultima_pagina = max(previa.pages, 1)
        if parametros.page > ultima_pagina:
            raise PaginaFueraDeRango(parametros.page, previa.pages)

        filas = await ordenes.listar_paginado_por_cliente(
            cliente_id=cliente.id,
            limit=parametros.size,
            offset=parametros.offset,
        )
        items = [resumen_desde_fila(fila) for fila in filas]

    return construir_pagina(items, total, parametros)


def _es_personal(actor: UsuarioAutenticado) -> bool:
    """Indica si la cuenta tiene alguno de los roles de personal del taller."""
    return any(actor.tiene_rol(rol) for rol in ROLES_DE_PERSONAL)


async def consultar_orden(
    uow: UnitOfWork,
    *,
    orden_id: int,
    actor: UsuarioAutenticado,
) -> OrdenDetalleResponse:
    """Devuelve el detalle de una orden para personal o para su dueño.

    El orden de las comprobaciones es el del diseño: primero ``404`` si la
    orden no existe y recién después la autorización, de modo que un no-dueño
    no puede distinguir una orden ajena existente de una inexistente. El
    personal (``ADMIN``, ``RECEPCION`` o ``MECANICO``) ve cualquier orden; una
    cuenta sin esos roles sólo ve las órdenes de los vehículos de su ficha, y
    una cuenta sin ficha nunca es dueña.

    El detalle llega resuelto desde ``listar_detalle`` con un número fijo de
    consultas: el vehículo de esa fila evita una lectura extra para comparar
    al dueño.
    """
    async with uow:
        ordenes = OrdenTrabajoRepository(uow.session)
        fila = await ordenes.listar_detalle(orden_id)
        if fila is None:
            raise OrdenNoEncontrada()

        if not _es_personal(actor):
            ficha = (
                None
                if actor.id is None
                else await ClienteRepository(uow.session).buscar_por_usuario(
                    actor.id
                )
            )
            if ficha is None or fila.vehiculo.cliente_id != ficha.id:
                raise SinPermisoSobreLaOrden()

    return detalle_desde_fila(fila)


async def listar_estados(uow: UnitOfWork) -> list[EstadoOrdenResponse]:
    """Devuelve el catálogo de estados en el orden en que se presenta.

    Es de sólo lectura: la API no crea, modifica ni elimina estados. El
    repositorio ordena por ``posicion`` y el indicador ``es_final`` viaja tal
    como lo declara el catálogo.
    """
    async with uow:
        estados = await EstadoOrdenRepository(uow.session).listar()

    return [EstadoOrdenResponse.model_validate(estado) for estado in estados]


async def _detalle_de(
    ordenes: OrdenTrabajoRepository,
    orden_id: int,
) -> OrdenDetalleResponse:
    """Lee el detalle ya transicionado y lo mapea al contrato de salida."""
    fila = await ordenes.listar_detalle(orden_id)
    if fila is None:
        raise RuntimeError("La orden recién transicionada no se pudo leer")
    return detalle_desde_fila(fila)


async def _agregar_historial(
    ordenes: OrdenTrabajoRepository,
    *,
    orden_id: int,
    desde_estado: str,
    hasta_estado: str,
    usuario_id: int,
) -> None:
    """Registra una transición de estado con su actor."""
    await ordenes.add(
        HistorialEstadoOrden(
            orden_id=orden_id,
            desde_estado=desde_estado,
            hasta_estado=hasta_estado,
            usuario_id=usuario_id,
        )
    )


async def iniciar_orden(
    uow: UnitOfWork,
    *,
    orden_id: int,
    actor: UsuarioAutenticado,
) -> OrdenDetalleResponse:
    """Inicia una orden ``PENDIENTE`` y la asigna a la cuenta actuante.

    El rol ``MECANICO`` lo exige la dependencia de la ruta, así que acá la
    secuencia es ``404`` si la orden no existe y ``409`` si su estado no es
    ``PENDIENTE``. La transición escribe el estado, el mecánico y la línea de
    historial dentro de la misma unidad de trabajo; un rechazo no escribe nada.
    """
    async with uow:
        ordenes = OrdenTrabajoRepository(uow.session)
        orden_actual = await ordenes.get(orden_id)
        if orden_actual is None:
            raise OrdenNoEncontrada()

        if orden_actual.estado != ESTADO_PENDIENTE:
            raise TransicionNoPermitida()

        actor_id = _id_del_actor(actor)
        orden_actual.estado = ESTADO_EN_REPARACION
        orden_actual.mecanico_id = actor_id
        await _agregar_historial(
            ordenes,
            orden_id=orden_id,
            desde_estado=ESTADO_PENDIENTE,
            hasta_estado=ESTADO_EN_REPARACION,
            usuario_id=actor_id,
        )
        respuesta = await _detalle_de(ordenes, orden_id)

    return respuesta


async def terminar_orden(
    uow: UnitOfWork,
    *,
    orden_id: int,
    actor: UsuarioAutenticado,
) -> OrdenDetalleResponse:
    """Termina una orden ``EN_REPARACION`` y consume el stock de sus ítems.

    El orden de las comprobaciones es el del diseño: ``404`` si no existe,
    después autorización (``ADMIN`` o el mecánico asignado) y recién entonces
    el estado, de modo que un ``403`` no revela el estado de la orden. Los
    repuestos se leen con ``SELECT ... FOR UPDATE`` y se validan todos antes
    de mutar: si uno no alcanza, ``StockInsuficiente`` sin ninguna escritura.

    Cada ítem deja un ``MovimientoStock`` con cantidad positiva, motivo de
    consumo, la orden y la cuenta que terminó. El estado, el historial y el
    stock se escriben en una sola unidad de trabajo: una falla posterior
    revierte todo. El total no se recalcula porque el precio quedó congelado.
    """
    async with uow:
        ordenes = OrdenTrabajoRepository(uow.session)
        orden_actual = await ordenes.get(orden_id)
        if orden_actual is None:
            raise OrdenNoEncontrada()

        if not actor.tiene_rol("ADMIN") and not (
            actor.id is not None and orden_actual.mecanico_id == actor.id
        ):
            raise SinPermisoSobreLaOrden()

        if orden_actual.estado != ESTADO_EN_REPARACION:
            raise TransicionNoPermitida()

        items = await ItemOrdenRepository(uow.session).listar_por_orden(orden_id)
        ids = [fila.item.repuesto_id for fila in items]
        repuestos = await RepuestoRepository(
            uow.session
        ).listar_por_ids_para_actualizar(ids)
        por_id = {repuesto.id: repuesto for repuesto in repuestos}

        for fila in items:
            repuesto = por_id.get(fila.item.repuesto_id)
            if repuesto is None or repuesto.stock < fila.item.cantidad:
                raise StockInsuficiente()

        actor_id = _id_del_actor(actor)
        movimientos = MovimientoStockRepository(uow.session)
        for fila in items:
            repuesto = por_id[fila.item.repuesto_id]
            repuesto.stock -= fila.item.cantidad
            await movimientos.add(
                MovimientoStock(
                    repuesto_id=fila.item.repuesto_id,
                    orden_id=orden_id,
                    usuario_id=actor_id,
                    cantidad=fila.item.cantidad,
                    motivo=MOTIVO_CONSUMO_ORDEN,
                )
            )

        orden_actual.estado = ESTADO_TERMINADA
        await _agregar_historial(
            ordenes,
            orden_id=orden_id,
            desde_estado=ESTADO_EN_REPARACION,
            hasta_estado=ESTADO_TERMINADA,
            usuario_id=actor_id,
        )
        respuesta = await _detalle_de(ordenes, orden_id)

    return respuesta


async def _es_dueno_del_vehiculo(
    uow: UnitOfWork,
    *,
    actor: UsuarioAutenticado,
    vehiculo_id: int,
) -> bool:
    """Indica si la cuenta tiene una ficha dueña del vehículo indicado.

    Una cuenta sin ficha nunca es dueña; una ficha distinta tampoco. El
    vehículo se lee vigente, así que uno dado de baja no habilita la acción.
    """
    if actor.id is None:
        return False

    ficha = await ClienteRepository(uow.session).buscar_por_usuario(actor.id)
    if ficha is None:
        return False

    vehiculo_actual = await VehiculoRepository(uow.session).get(vehiculo_id)
    return vehiculo_actual is not None and vehiculo_actual.cliente_id == ficha.id


async def cancelar_orden(
    uow: UnitOfWork,
    *,
    orden_id: int,
    actor: UsuarioAutenticado,
) -> OrdenDetalleResponse:
    """Cancela una orden ``PENDIENTE`` a pedido del personal o de su dueño.

    El permiso se evalúa antes que el estado: ``ADMIN``, ``RECEPCION`` o el
    dueño del vehículo pueden cancelar; cualquier otra cuenta recibe
    ``SinPermisoSobreLaOrden`` aunque el estado tampoco lo permitiera. Recién
    después se exige ``PENDIENTE``; la transición deja su línea de historial.
    """
    async with uow:
        ordenes = OrdenTrabajoRepository(uow.session)
        orden_actual = await ordenes.get(orden_id)
        if orden_actual is None:
            raise OrdenNoEncontrada()

        if not (
            actor.tiene_rol("ADMIN")
            or actor.tiene_rol("RECEPCION")
            or await _es_dueno_del_vehiculo(
                uow,
                actor=actor,
                vehiculo_id=orden_actual.vehiculo_id,
            )
        ):
            raise SinPermisoSobreLaOrden()

        if orden_actual.estado != ESTADO_PENDIENTE:
            raise TransicionNoPermitida()

        actor_id = _id_del_actor(actor)
        orden_actual.estado = ESTADO_CANCELADA
        await _agregar_historial(
            ordenes,
            orden_id=orden_id,
            desde_estado=ESTADO_PENDIENTE,
            hasta_estado=ESTADO_CANCELADA,
            usuario_id=actor_id,
        )
        respuesta = await _detalle_de(ordenes, orden_id)

    return respuesta
