"""Carga de datos iniciales (seed).

Este archivo se ejecuta como parte de la puesta en marcha del proyecto.
Vacía las tablas de dominio y carga el catálogo de estados, los usuarios con
sus roles vigentes, los clientes y vehículos, los repuestos con su stock
inicial, las órdenes de trabajo con sus ítems e historial, el historial de
precios y el evento de seguridad inicial.

El catálogo de estados se carga primero, porque todo lo que tiene un estado
apunta a él y sin sus filas no se puede crear ninguna orden.

Sobre la limpieza y RN-15
-------------------------
Las tablas ``historial_estado_orden``, ``movimiento_stock`` e
``historial_precio_repuesto`` son de sólo agregado: sus disparadores
``BEFORE UPDATE OR DELETE FOR EACH ROW`` rechazan cualquier modificación o
borrado de filas. La limpieza usa un único ``TRUNCATE TABLE ... RESTART
IDENTITY CASCADE``, que no dispara los disparadores ``FOR EACH ROW`` (sólo
dispararía un eventual ``BEFORE TRUNCATE``, que estas tablas no tienen). Por
eso la rutina es idempotente sin deshabilitar los disparadores y sin violar
RN-15: no se actualiza ni se borra ninguna fila histórica con ``UPDATE`` o
``DELETE``.

Todo se ejecuta dentro de una sola transacción: si cualquier inserción falla,
la limpieza previa y las inserciones se revierten juntas.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import create_engine_and_session_factory
from app.core.security import hash_password
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import (
    EstadoOrden,
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)
from app.modules.repuestos.models import (
    HistorialPrecioRepuesto,
    MovimientoStock,
    Repuesto,
)
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    Usuario,
)

# Contraseña de mentira compartida por todas las cuentas iniciales. Vive sólo
# en este archivo; el hash real se calcula con bcrypt en cada ejecución.
PASSWORD_INICIAL = "Secreto123!"

# Las 13 tablas de dominio. ``alembic_version`` no se toca: el esquema y la
# revisión de migraciones deben sobrevivir a la recarga de datos.
TABLAS_DOMINIO: tuple[str, ...] = (
    "historial_estado_orden",
    "historial_precio_repuesto",
    "movimiento_stock",
    "item_orden",
    "orden_trabajo",
    "vehiculo",
    "cliente",
    "asignacion_rol",
    "intento_acceso",
    "evento_seguridad",
    "estado_orden",
    "repuesto",
    "usuario",
)


async def limpiar_tablas(session: AsyncSession) -> None:
    """Vacía las tablas de dominio en una sola sentencia.

    ``TRUNCATE ... RESTART IDENTITY CASCADE`` reinicia las secuencias para que
    los identificadores sean deterministas, y ``CASCADE`` alcanza a cualquier
    tabla que dependa de las listadas. No dispara los disparadores de sólo
    agregado, que son ``FOR EACH ROW`` sobre ``UPDATE``/``DELETE``.
    """
    tablas = ", ".join(TABLAS_DOMINIO)
    await session.execute(
        text(f"TRUNCATE TABLE {tablas} RESTART IDENTITY CASCADE")
    )


async def cargar_datos_iniciales(session: AsyncSession) -> None:
    """Limpia y carga el conjunto de datos inicial completo.

    Las claves foráneas se resuelven con ``flush()`` después de cada grupo de
    inserciones: así el ORM escribe las filas y devuelve los ``id`` generados
    antes de usarlos en el grupo siguiente. La transacción la maneja quien
    llama a esta función.
    """
    await limpiar_tablas(session)

    # 1. Catálogo de estados. Es lo primero porque ``orden_trabajo.estado`` y
    #    ``historial_estado_orden`` apuntan a él.
    estados = [
        EstadoOrden(
            codigo="PENDIENTE",
            descripcion="Orden creada, pendiente de inicio de reparación",
            posicion=1,
            es_final=False,
        ),
        EstadoOrden(
            codigo="EN_REPARACION",
            descripcion="Vehículo en reparación",
            posicion=2,
            es_final=False,
        ),
        EstadoOrden(
            codigo="TERMINADA",
            descripcion="Reparación terminada y entregada",
            posicion=3,
            es_final=True,
        ),
        EstadoOrden(
            codigo="CANCELADA",
            descripcion="Orden cancelada antes de terminar",
            posicion=4,
            es_final=True,
        ),
    ]
    session.add_all(estados)
    await session.flush()

    # 2. Usuarios. Todos comparten la misma contraseña de mentira.
    password_hash = await hash_password(PASSWORD_INICIAL)
    usuarios = [
        Usuario(
            email="admin@example.com",
            nombre="Admin Principal",
            password_hash=password_hash,
        ),
        Usuario(
            email="admin2@example.com",
            nombre="Admin Secundario",
            password_hash=password_hash,
        ),
        Usuario(
            email="recepcion@example.com",
            nombre="Recepción",
            password_hash=password_hash,
        ),
        Usuario(
            email="mecanico@example.com",
            nombre="Mecánico Uno",
            password_hash=password_hash,
        ),
        Usuario(
            email="mecanico2@example.com",
            nombre="Mecánico Dos",
            password_hash=password_hash,
        ),
        Usuario(
            email="cliente@example.com",
            nombre="Laura Cliente",
            password_hash=password_hash,
            debe_cambiar_password=False,
        ),
        Usuario(
            email="nuevo@example.com",
            nombre="Nuevo Mecánico",
            password_hash=password_hash,
            debe_cambiar_password=True,
        ),
    ]
    session.add_all(usuarios)
    await session.flush()

    usuario_id = {usuario.email: usuario.id for usuario in usuarios}
    admin_id = usuario_id["admin@example.com"]
    mecanico_id = usuario_id["mecanico@example.com"]
    cliente_usuario_id = usuario_id["cliente@example.com"]

    # 3. Asignación de un rol vigente por usuario, otorgada por el admin.
    roles_por_email = {
        "admin@example.com": "ADMIN",
        "admin2@example.com": "ADMIN",
        "recepcion@example.com": "RECEPCION",
        "mecanico@example.com": "MECANICO",
        "mecanico2@example.com": "MECANICO",
        "cliente@example.com": "CLIENTE",
        "nuevo@example.com": "MECANICO",
    }
    asignaciones = [
        AsignacionRol(
            usuario_id=usuario_id[email],
            rol=rol,
            otorgada_por=admin_id,
        )
        for email, rol in roles_por_email.items()
    ]
    session.add_all(asignaciones)
    await session.flush()

    # 4. Clientes. Laura tiene cuenta; Jorge no.
    laura = Cliente(
        usuario_id=cliente_usuario_id,
        nombre="Laura Cliente",
        documento="30111222",
        telefono="555-0101",
    )
    jorge = Cliente(
        usuario_id=None,
        nombre="Jorge Cliente",
        documento="28999888",
        telefono="555-0102",
    )
    session.add_all([laura, jorge])
    await session.flush()

    # 5. Vehículos, en el orden que fija los identificadores del seed.
    vehiculos = [
        Vehiculo(
            cliente_id=laura.id,
            patente="AC456EF",
            marca="Toyota",
            modelo="Corolla",
            anio=2020,
        ),
        Vehiculo(
            cliente_id=laura.id,
            patente="AB123CD",
            marca="Ford",
            modelo="Focus",
            anio=2018,
        ),
        Vehiculo(
            cliente_id=jorge.id,
            patente="JOR123",
            marca="Chevrolet",
            modelo="Onix",
            anio=2019,
        ),
    ]
    session.add_all(vehiculos)
    await session.flush()

    vehiculo_laura_id = vehiculos[0].id
    vehiculo_jorge_id = vehiculos[2].id

    # 6. Repuestos con su precio y su stock actual.
    repuestos = [
        Repuesto(
            codigo="FIL-001",
            descripcion="Filtro de aceite",
            precio=Decimal("8500.00"),
            stock=10,
        ),
        Repuesto(
            codigo="FRE-010",
            descripcion="Pastillas de freno delanteras",
            precio=Decimal("32000.00"),
            stock=4,
        ),
        Repuesto(
            codigo="BUJ-020",
            descripcion="Bujía de encendido",
            precio=Decimal("5000.00"),
            stock=2,
        ),
        Repuesto(
            codigo="ACE-530",
            descripcion="Aceite 5W30 por litro",
            precio=Decimal("12000.00"),
            stock=20,
        ),
    ]
    session.add_all(repuestos)
    await session.flush()

    repuesto_id = {repuesto.codigo: repuesto.id for repuesto in repuestos}

    # 7. Movimiento "Stock inicial" por cada repuesto, con su stock actual.
    movimientos = [
        MovimientoStock(
            repuesto_id=repuesto.id,
            orden_id=None,
            usuario_id=admin_id,
            cantidad=repuesto.stock,
            motivo="Stock inicial",
        )
        for repuesto in repuestos
    ]
    session.add_all(movimientos)
    await session.flush()

    # 8. Historial de precios: el filtro de aceite subió de 8000 a 8500.
    historial_precio = HistorialPrecioRepuesto(
        repuesto_id=repuesto_id["FIL-001"],
        usuario_id=admin_id,
        precio_anterior=Decimal("8000.00"),
        precio_nuevo=Decimal("8500.00"),
    )
    session.add(historial_precio)
    await session.flush()

    # 9. Órdenes de trabajo.
    orden_1 = OrdenTrabajo(
        vehiculo_id=vehiculo_laura_id,
        mecanico_id=None,
        estado="PENDIENTE",
        falla="Ruido en el motor",
        total=Decimal("0.00"),
    )
    orden_2 = OrdenTrabajo(
        vehiculo_id=vehiculo_jorge_id,
        mecanico_id=mecanico_id,
        estado="EN_REPARACION",
        falla="Falla de encendido",
        total=Decimal("20000.00"),
    )
    session.add_all([orden_1, orden_2])
    await session.flush()

    # 10. Ítems de la orden 2: 4 bujías a 5000 cada una (total 20000). El
    #     único repuesto se repite como cantidad, porque el modelo prohíbe
    #     dos filas del mismo repuesto en una orden.
    item_orden_2 = ItemOrden(
        orden_id=orden_2.id,
        repuesto_id=repuesto_id["BUJ-020"],
        cantidad=4,
        precio_unitario=Decimal("5000.00"),
    )
    session.add(item_orden_2)
    await session.flush()

    # 11. Historial de estados: alta de cada orden y la transición de la 2.
    historial_orden = [
        HistorialEstadoOrden(
            orden_id=orden_1.id,
            desde_estado=None,
            hasta_estado="PENDIENTE",
            usuario_id=admin_id,
        ),
        HistorialEstadoOrden(
            orden_id=orden_2.id,
            desde_estado=None,
            hasta_estado="PENDIENTE",
            usuario_id=admin_id,
        ),
        HistorialEstadoOrden(
            orden_id=orden_2.id,
            desde_estado="PENDIENTE",
            hasta_estado="EN_REPARACION",
            usuario_id=mecanico_id,
        ),
    ]
    session.add_all(historial_orden)
    await session.flush()

    # 12. Evento de seguridad de la carga inicial.
    evento = EventoSeguridad(
        actor="SISTEMA",
        accion="Carga de los datos iniciales",
    )
    session.add(evento)
    await session.flush()


async def main() -> None:
    """Punto de entrada: carga los datos iniciales en una única transacción."""
    engine, session_factory = create_engine_and_session_factory()
    try:
        async with session_factory() as session:
            async with session.begin():
                await cargar_datos_iniciales(session)
        print("seed.py: datos iniciales cargados correctamente.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
