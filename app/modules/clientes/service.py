"""Servicio del módulo de clientes.

El servicio no conoce HTTP: recibe la ``UnitOfWork`` que arma el router y, en
las escrituras, la cuenta actuante. Lanza errores de dominio de ``errors.py`` y
el router los traduce. Ningún método confirma: la confirmación pertenece a la
unidad de trabajo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.repository import ConflictoDeIntegridad
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.errors import (
    AnioFueraDeRango,
    ClienteNoEncontrado,
    DocumentoYaRegistrado,
    PatenteYaRegistrada,
    SinFichaDeCliente,
    VehiculoConOrdenesAbiertas,
    VehiculoNoEncontrado,
)
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.clientes.repository import ClienteRepository, VehiculoRepository
from app.modules.clientes.schemas import (
    ANIO_MAXIMO,
    ANIO_MINIMO,
    AltaClienteRequest,
    AltaVehiculoRequest,
)
from app.modules.clientes.verificacion import VerificadorOrdenesAbiertas
from app.modules.usuarios.models import Usuario

__all__ = [
    "ClienteConVehiculos",
    "crear_cliente",
    "crear_vehiculo",
    "consultar_cliente",
    "dar_de_baja_vehiculo",
    "listar_mis_vehiculos",
]


@dataclass(frozen=True)
class ClienteConVehiculos:
    """Ficha de un cliente junto con sus vehículos vigentes."""

    cliente: Cliente
    vehiculos: list[Vehiculo]


def _clave_primaria(entidad: Cliente | Vehiculo) -> int:
    """Devuelve la clave ya asignada o falla si el ``flush`` no la generó."""
    if entidad.id is None:
        raise RuntimeError("La entidad no obtuvo su clave primaria al persistirse")
    return entidad.id


async def crear_cliente(
    uow: UnitOfWork,
    datos: AltaClienteRequest,
    actor: Usuario,
) -> Cliente:
    """Crea la ficha de un cliente del taller.

    El actor se acepta por simetría con las altas auditadas, pero la ficha no
    escribe eventos de seguridad: el spec no lo exige. Solo el ``add`` de la
    ficha puede chocar con el documento único; un conflicto posterior no es un
    documento repetido y se propaga tal cual.
    """
    async with uow:
        clientes = ClienteRepository(uow.session)

        try:
            cliente = await clientes.add(
                Cliente(
                    nombre=datos.nombre,
                    documento=datos.documento,
                    telefono=datos.telefono,
                )
            )
        except ConflictoDeIntegridad as error:
            raise DocumentoYaRegistrado() from error

    _clave_primaria(cliente)
    return cliente


async def consultar_cliente(
    uow: UnitOfWork,
    cliente_id: int,
) -> ClienteConVehiculos:
    """Devuelve la ficha de un cliente con sus vehículos vigentes.

    Son dos consultas acotadas por cliente (la ficha y sus vehículos) en lugar
    de cargar la relación: evita el N+1 y no necesita un ``primaryjoin``
    filtrado por baja. Si la ficha no existe, falla antes de consultar
    vehículos.
    """
    async with uow:
        cliente = await ClienteRepository(uow.session).get(cliente_id)
        if cliente is None:
            raise ClienteNoEncontrado()

        vehiculos = await VehiculoRepository(
            uow.session
        ).listar_vigentes_por_cliente(_clave_primaria(cliente))

    return ClienteConVehiculos(cliente=cliente, vehiculos=vehiculos)


async def crear_vehiculo(
    uow: UnitOfWork,
    cliente_id: int,
    datos: AltaVehiculoRequest,
    actor: Usuario,
) -> Vehiculo:
    """Registra un vehículo para un cliente existente.

    La patente llega ya normalizada por el contrato y el año ya validado: el
    ``CHECK`` de la base es la última red, no la primera. No se consulta la
    patente de antemano porque la unicidad entre vigentes la decide el índice
    único parcial; sólo el ``add`` del vehículo puede chocar con él.

    El año se vuelve a comprobar acá como defensa en profundidad: un llamador
    que construya el contrato sin pasar por sus validadores (por ejemplo, un
    seed o una prueba) recibe ``AnioFueraDeRango`` y no un error del motor. La
    comprobación va después de resolver el cliente para preservar el orden
    ``404`` antes de ``422``.

    El actor se acepta por simetría con las altas auditadas; el vehículo no
    escribe eventos de seguridad.
    """
    async with uow:
        if await ClienteRepository(uow.session).get(cliente_id) is None:
            raise ClienteNoEncontrado()

        if not ANIO_MINIMO <= datos.anio <= ANIO_MAXIMO:
            raise AnioFueraDeRango()

        vehiculos = VehiculoRepository(uow.session)
        try:
            vehiculo = await vehiculos.add(
                Vehiculo(
                    cliente_id=cliente_id,
                    patente=datos.patente,
                    marca=datos.marca,
                    modelo=datos.modelo,
                    anio=datos.anio,
                )
            )
        except ConflictoDeIntegridad as error:
            raise PatenteYaRegistrada() from error

    _clave_primaria(vehiculo)
    return vehiculo


async def dar_de_baja_vehiculo(
    uow: UnitOfWork,
    vehiculo_id: int,
    actor: Usuario,
    verificador: VerificadorOrdenesAbiertas,
) -> None:
    """Da de baja lógica un vehículo vigente sin órdenes abiertas.

    ``VehiculoRepository.get`` ya excluye las filas dadas de baja, así que un
    vehículo inexistente y uno ya dado de baja producen el mismo ``404`` y la
    marca original se conserva.

    El orden importa: se verifica que no haya órdenes abiertas **antes** de
    escribir, de modo que un rechazo deja el vehículo vigente. El verificador
    es obligatorio: el router inyecta el que consulta ``orden_trabajo``; el
    servicio sólo conoce el protocolo y no decide cómo se cuentan las órdenes.
    """
    async with uow:
        vehiculos = VehiculoRepository(uow.session)

        vehiculo = await vehiculos.get(vehiculo_id)
        if vehiculo is None:
            raise VehiculoNoEncontrado()

        if await verificador.contar_abiertas(vehiculo_id) > 0:
            raise VehiculoConOrdenesAbiertas()

        await vehiculos.soft_delete(vehiculo)


async def listar_mis_vehiculos(
    uow: UnitOfWork,
    usuario_id: int,
) -> list[Vehiculo]:
    """Lista los vehículos vigentes de la ficha del cliente autenticado.

    La ficha se resuelve por ``usuario_id``, nunca por un cliente id que venga
    del llamador: así una cuenta no puede pedir los vehículos de otra. Si la
    cuenta no tiene ficha, el cliente no puede tener vehículos propios y la
    respuesta es ``403`` (``SinFichaDeCliente``).
    """
    async with uow:
        cliente = await ClienteRepository(uow.session).buscar_por_usuario(usuario_id)
        if cliente is None:
            raise SinFichaDeCliente()

        vehiculos = await VehiculoRepository(
            uow.session
        ).listar_vigentes_por_cliente(_clave_primaria(cliente))

    return vehiculos
