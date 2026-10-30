"""Servicio de administración de usuarios y roles.

El servicio no conoce HTTP: recibe la ``UnitOfWork`` que arma el router, la
cuenta actuante y, cuando depende del reloj, un ``reloj`` inyectable. Lanza
errores de dominio de ``errors.py`` y el router los traduce.

Toda operación auditable escribe su evento **dentro** de la misma unidad de
trabajo: si el evento fallara, la operación completa se revierte. Una
operación rechazada no deja evento, porque la excepción sale antes de
registrarlo.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.core.paginacion import ParametrosPagina, construir_pagina
from app.core.repository import ConflictoDeIntegridad
from app.core.security import hash_password
from app.core.unit_of_work import UnitOfWork
from app.modules.auth.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    UsuarioRepository,
)
from app.modules.auth.service import ahora_utc
from app.modules.usuarios.errors import (
    AsignacionNoEncontrada,
    CorreoYaRegistrado,
    PaginaFueraDeRango,
    RevocacionPropiaNoPermitida,
    RolYaAsignado,
    UltimoAdministrador,
    UsuarioNoEncontrado,
)
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.usuarios.schemas import (
    AltaUsuarioRequest,
    AsignacionRolRequest,
    AsignacionRolResponse,
    EventoSeguridadResponse,
    PaginaResponse,
    UsuarioCreadoResponse,
)

# Formato del actor en ``evento_seguridad``. Se usa el ``id`` y no el correo
# porque ``actor`` es ``VARCHAR(100)`` y ``usuario.email`` es ``VARCHAR(255)``:
# un correo largo rompería el ``INSERT`` y, con él, la operación auditada.
PREFIJO_ACTOR_USUARIO = "USUARIO"

ACCION_ALTA_USUARIO_PERSONAL = "ALTA_USUARIO_PERSONAL"
ACCION_ASIGNACION_ROL = "ASIGNACION_ROL"
ACCION_REVOCACION_ROL = "REVOCACION_ROL"

# Único rol con invariante global: el sistema no puede quedarse sin ADMIN.
ROL_ADMIN = "ADMIN"


def _clave_primaria(usuario: Usuario) -> int:
    """Devuelve la clave ya asignada o falla si el ``flush`` no la generó."""
    if usuario.id is None:
        raise RuntimeError("La cuenta no obtuvo su clave primaria al persistirse")
    return usuario.id


def _actor_de(usuario: Usuario) -> str:
    """Arma el actor textual del evento para una cuenta concreta."""
    return f"{PREFIJO_ACTOR_USUARIO}:{_clave_primaria(usuario)}"


def _clave_asignacion(asignacion: AsignacionRol) -> int:
    """Devuelve la clave de la asignación o falla si el ``flush`` no la generó."""
    if asignacion.id is None:
        raise RuntimeError("La asignación no obtuvo su clave primaria al persistirse")
    return asignacion.id


def _clave_evento(evento: EventoSeguridad) -> int:
    """Devuelve la clave del evento ya persistido."""
    if evento.id is None:
        raise RuntimeError("El evento no obtuvo su clave primaria al persistirse")
    return evento.id


def _respuesta_de_asignacion(asignacion: AsignacionRol) -> AsignacionRolResponse:
    """Serializa una asignación ya persistida."""
    return AsignacionRolResponse(
        id=_clave_asignacion(asignacion),
        rol=asignacion.rol,
        desde=asignacion.desde,
        vence_en=asignacion.vence_en,
        revocada_en=asignacion.revocada_en,
        otorgada_por=asignacion.otorgada_por,
    )


async def crear_usuario_personal(
    uow: UnitOfWork,
    datos: AltaUsuarioRequest,
    actor: Usuario,
) -> UsuarioCreadoResponse:
    """Crea una cuenta de personal sin roles y con cambio de contraseña pendiente.

    El hash se calcula antes de abrir la transacción para no retener la
    conexión durante el costo de bcrypt. La cuenta nace ``activo=True`` y sin
    asignaciones: puede autenticarse, pero recibe ``403`` en todo el grupo
    protegido hasta que un administrador le asigne un rol.

    No se emite token ni cookie: quien crea la cuenta no inicia sesión como el
    usuario creado.
    """
    password_hash = await hash_password(datos.password)

    async with uow:
        usuarios = UsuarioRepository(uow.session)
        eventos = EventoSeguridadRepository(uow.session)

        # Solo el alta de la cuenta puede chocar con el correo único; un
        # conflicto posterior (por ejemplo en el evento) no es un correo
        # duplicado y debe propagarse tal cual.
        try:
            usuario = await usuarios.add(
                Usuario(
                    email=datos.email,
                    nombre=datos.nombre,
                    password_hash=password_hash,
                    activo=True,
                    debe_cambiar_password=True,
                )
            )
        except ConflictoDeIntegridad as error:
            raise CorreoYaRegistrado() from error

        await eventos.registrar(_actor_de(actor), ACCION_ALTA_USUARIO_PERSONAL)

    return UsuarioCreadoResponse(
        id=_clave_primaria(usuario),
        email=usuario.email,
        nombre=usuario.nombre,
        activo=usuario.activo,
        debe_cambiar_password=usuario.debe_cambiar_password,
    )


async def asignar_rol(
    uow: UnitOfWork,
    usuario_id: int,
    datos: AsignacionRolRequest,
    actor: Usuario,
    *,
    reloj: Callable[[], datetime] = ahora_utc,
) -> AsignacionRolResponse:
    """Otorga un rol a una cuenta existente, con vencimiento opcional.

    ``desde`` y ``otorgada_por`` se fijan acá, no se aceptan del cliente: la
    auditoría de cuándo y quién otorgó el rol no debe poder falsearse.

    Si el rol ya está abierto y vigente, la operación se rechaza. Si está
    abierto pero vencido, se revoca y se hace ``flush()`` **antes** del
    ``INSERT`` de la nueva: el índice único parcial solo excluye las filas
    revocadas, no las vencidas, así que sin ese orden el alta choca.
    """
    ahora = reloj()

    async with uow:
        usuarios = UsuarioRepository(uow.session)
        asignaciones = AsignacionRolRepository(uow.session)
        eventos = EventoSeguridadRepository(uow.session)

        if await usuarios.get(usuario_id) is None:
            raise UsuarioNoEncontrado()

        abierta = await asignaciones.buscar_abierta(usuario_id, datos.rol)
        if abierta is not None:
            if abierta.vence_en is None or abierta.vence_en > ahora:
                raise RolYaAsignado(datos.rol)
            abierta.revocada_en = ahora
            await asignaciones.flush()

        nueva = await asignaciones.add(
            AsignacionRol(
                usuario_id=usuario_id,
                rol=datos.rol,
                desde=ahora,
                vence_en=datos.vence_en,
                otorgada_por=_clave_primaria(actor),
            )
        )
        await eventos.registrar(_actor_de(actor), ACCION_ASIGNACION_ROL)

    return _respuesta_de_asignacion(nueva)

async def revocar_rol(
    uow: UnitOfWork,
    usuario_id: int,
    rol: str,
    actor: Usuario,
    *,
    reloj: Callable[[], datetime] = ahora_utc,
) -> AsignacionRolResponse:
    """Revoca la asignación abierta de un rol, sin borrar la fila.

    El orden de rechazo importa: primero la autoprotección (un administrador no
    se revoca a sí mismo) y después la invariante global (el sistema no puede
    quedarse sin administradores vigentes). Así el mensaje es el correcto
    cuando ambas condiciones se cumplen a la vez.

    La comprobación de la invariante es *check-then-act*: dos administradores
    podrían revocarse mutuamente en paralelo. Se acepta como limitación
    documentada; resolverla requiere bloqueo de filas.
    """
    ahora = reloj()

    async with uow:
        usuarios = UsuarioRepository(uow.session)
        asignaciones = AsignacionRolRepository(uow.session)
        eventos = EventoSeguridadRepository(uow.session)

        if await usuarios.get(usuario_id) is None:
            raise UsuarioNoEncontrado()

        abierta = await asignaciones.buscar_abierta(usuario_id, rol)
        if abierta is None:
            raise AsignacionNoEncontrada()

        if rol == ROL_ADMIN and usuario_id == _clave_primaria(actor):
            raise RevocacionPropiaNoPermitida()

        if rol == ROL_ADMIN and (
            await asignaciones.contar_admin_vigentes(
                ahora,
                excluir_id=_clave_asignacion(abierta),
            )
            == 0
        ):
            raise UltimoAdministrador()

        abierta.revocada_en = ahora
        await asignaciones.flush()
        await eventos.registrar(_actor_de(actor), ACCION_REVOCACION_ROL)

    return _respuesta_de_asignacion(abierta)


async def consultar_roles(
    uow: UnitOfWork,
    usuario_id: int,
) -> list[AsignacionRolResponse]:
    """Devuelve el historial de roles de una cuenta existente.

    Incluye asignaciones abiertas, vencidas y revocadas: el endpoint sirve
    para auditar y el estado se lee en ``vence_en`` y ``revocada_en``. No se
    pagina porque la cantidad de asignaciones por cuenta está acotada por el
    catálogo de roles y su historial.
    """
    async with uow:
        usuarios = UsuarioRepository(uow.session)
        if await usuarios.get(usuario_id) is None:
            raise UsuarioNoEncontrado()

        asignaciones = await AsignacionRolRepository(
            uow.session
        ).listar_historial(usuario_id)

    return [_respuesta_de_asignacion(asignacion) for asignacion in asignaciones]


async def consultar_eventos(
    uow: UnitOfWork,
    parametros: ParametrosPagina,
) -> PaginaResponse[EventoSeguridadResponse]:
    """Devuelve una página del historial de eventos, del más reciente al más viejo.

    El total se consulta antes de traer las filas: sin él no se puede saber si
    la página pedida existe, y traer una página inexistente solo para
    descartarla cuesta una consulta de más. La página final se arma con
    ``construir_pagina`` para no duplicar el cálculo de ``pages``.
    """
    async with uow:
        eventos = EventoSeguridadRepository(uow.session)
        total = await eventos.contar()

        # Página vacía solo para reutilizar el cálculo de ``pages`` antes de
        # decidir si vale la pena traer filas.
        previa = construir_pagina([], total, parametros)
        if parametros.page > previa.pages:
            raise PaginaFueraDeRango(parametros.page, previa.pages)

        filas = await eventos.listar_paginado(
            limit=parametros.size,
            offset=parametros.offset,
        )

    pagina = construir_pagina(filas, total, parametros)
    return PaginaResponse[EventoSeguridadResponse](
        items=[
            EventoSeguridadResponse(
                id=_clave_evento(evento),
                cuando=evento.cuando,
                actor=evento.actor,
                accion=evento.accion,
            )
            for evento in pagina.items
        ],
        total=pagina.total,
        page=pagina.page,
        size=pagina.size,
        pages=pagina.pages,
    )
