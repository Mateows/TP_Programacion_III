"""Servicio de autenticación: registro, login, sesión y cambio de contraseña.

El servicio no conoce HTTP: recibe la ``UnitOfWork`` que arma el router, la
``SessionFactory`` para el registro de intentos y un reloj inyectable, y lanza
errores de dominio de ``errors.py``. Esa separación permite probarlo sin base
de datos ni ``TestClient``.

Las escrituras ocurren dentro de la unidad de trabajo que recibe; el único
registro que se confirma aparte es el intento de acceso, para que sobreviva a
cualquier error posterior de la petición.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as TiempoDeEsperaAgotado

from app.core.config import settings
from app.core.repository import ConflictoDeIntegridad
from app.core.security import (
    JWTPayload,
    create_access_token,
    hash_ficticio,
    hash_password,
    verify_password,
)
from app.core.unit_of_work import UnitOfWork
from app.modules.auth.errors import (
    CorreoYaRegistrado,
    CredencialesInvalidas,
    LimiteDeIntentosExcedido,
    PasswordInvalida,
)
from app.modules.auth.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)
from app.modules.auth.schemas import (
    CambioPasswordRequest,
    LoginRequest,
    RegistroRequest,
    SesionResponse,
    validar_password,
)
from app.modules.clientes.errors import DocumentoYaRegistrado
from app.modules.clientes.models import Cliente
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.models import AsignacionRol, Usuario

if TYPE_CHECKING:
    # La fábrica de sesiones vive en ``app.core.database``; se importa solo
    # para tipar y no arrastrar FastAPI al servicio.
    from app.core.database import SessionFactory

logger = logging.getLogger(__name__)

# Constantes reutilizables por C-04 y C-09 (design, decisión 10).
ACTOR_SISTEMA = "SISTEMA"
ACCION_REGISTRO_USUARIO = "REGISTRO_USUARIO"
ACCION_CAMBIO_PASSWORD = "CAMBIO_PASSWORD"
ROL_CLIENTE = "CLIENTE"


def ahora_utc() -> datetime:
    """Reloj de la aplicación, fuente de ``iat`` y ``password_cambiada_en``."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class SesionEmitida:
    """Resultado de un registro, login o cambio de contraseña.

    Lleva el token para que el router lo ponga en la cookie ``access_token``:
    el token nunca viaja en el cuerpo de la respuesta.
    """

    usuario: Usuario
    token: str
    roles: list[str]

    @property
    def debe_cambiar_password(self) -> bool:
        """Estado del cambio obligatorio según la cuenta ya persistida."""
        return self.usuario.debe_cambiar_password

    @property
    def expira_en_segundos(self) -> int:
        """Vigencia del token, para ``Max-Age`` y para el cuerpo del mensaje."""
        return settings.JWT_EXPIRES_MINUTES * 60


def payload_de_sesion(usuario: Usuario, roles: list[str]) -> JWTPayload:
    """Arma los claims de sesión: ``sub``, ``roles`` y cambio pendiente.

    ``iat`` y ``exp`` los agrega ``create_access_token``.
    """
    return {
        "sub": str(usuario.id),
        "roles": list(roles),
        "debe_cambiar_password": usuario.debe_cambiar_password,
    }


def _clave_primaria(usuario: Usuario) -> int:
    """Devuelve la clave ya asignada o falla si el ``flush`` no la generó."""
    if usuario.id is None:
        raise RuntimeError("La cuenta no obtuvo su clave primaria al persistirse")
    return usuario.id


async def registrar_cuenta(uow: UnitOfWork, datos: RegistroRequest) -> SesionEmitida:
    """Crea la cuenta, su rol ``CLIENTE``, la ficha y el evento de alta.

    El hash se calcula antes de abrir la transacción para no retener la
    conexión durante el costo de bcrypt (KB 07, Flujo 1). La cuenta, el rol
    ``CLIENTE`` y la ficha de cliente (RN-02) se escriben en la misma unidad:
    si alguna falla, la unidad revierte y no queda ninguna de las tres.

    Cada ``add`` que puede chocar con una restricción traduce el conflicto a
    su error de dominio: el correo único sólo puede fallar en el alta de la
    cuenta y el documento único sólo en el alta de la ficha. Un conflicto en
    cualquier otro punto no es ninguno de los dos y se propaga tal cual.
    """
    password_hash = await hash_password(datos.password)

    async with uow:
        usuarios = UsuarioRepository(uow.session)
        asignaciones = AsignacionRolRepository(uow.session)
        clientes = ClienteRepository(uow.session)
        eventos = EventoSeguridadRepository(uow.session)

        try:
            usuario = await usuarios.add(
                Usuario(
                    email=datos.email,
                    nombre=datos.nombre,
                    password_hash=password_hash,
                )
            )
        except ConflictoDeIntegridad as error:
            raise CorreoYaRegistrado() from error

        usuario_id = _clave_primaria(usuario)
        await asignaciones.add(
            AsignacionRol(usuario_id=usuario_id, rol=ROL_CLIENTE)
        )
        try:
            await clientes.add(
                Cliente(
                    usuario_id=usuario_id,
                    nombre=datos.nombre,
                    documento=datos.documento,
                    telefono=datos.telefono,
                )
            )
        except ConflictoDeIntegridad as error:
            raise DocumentoYaRegistrado() from error

        await eventos.registrar(ACTOR_SISTEMA, ACCION_REGISTRO_USUARIO)

    return SesionEmitida(
        usuario=usuario,
        token=create_access_token(payload_de_sesion(usuario, [ROL_CLIENTE])),
        roles=[ROL_CLIENTE],
    )


def _retry_after(fallo_mas_antiguo: datetime | None, ahora: datetime) -> int:
    """Segundos hasta que el fallo más antiguo salga de la ventana."""
    if fallo_mas_antiguo is None:
        return settings.LOGIN_VENTANA_SEGUNDOS

    libre_en = fallo_mas_antiguo + timedelta(seconds=settings.LOGIN_VENTANA_SEGUNDOS)
    return max(1, math.ceil((libre_en - ahora).total_seconds()))


async def _registrar_intento(
    session_factory: SessionFactory,
    email: str,
    ip: str,
    *,
    exito: bool,
    cuando: datetime,
) -> None:
    """Confirma el intento en su propia transacción, fuera de la petición.

    Un fallo operativo de la auditoría (base no disponible, conexión perdida,
    espera de pool agotada) o un conflicto de integridad se registra en el log
    y no cambia la respuesta al cliente: el intento no puede tumbar el login
    ni el 401. Cualquier otro error es un defecto del programa y se propaga en
    lugar de silenciarse.
    """
    try:
        async with session_factory() as sesion:
            async with UnitOfWork(sesion) as uow:
                await IntentoAccesoRepository(uow.session).registrar(
                    email,
                    ip,
                    exito=exito,
                    cuando=cuando,
                )
    except (
        OperationalError,
        InterfaceError,
        TiempoDeEsperaAgotado,
        ConflictoDeIntegridad,
    ):
        logger.exception("No se pudo registrar el intento de acceso")


async def iniciar_sesion(
    uow: UnitOfWork,
    session_factory: SessionFactory,
    datos: LoginRequest,
    ip: str,
    *,
    reloj: Callable[[], datetime] = ahora_utc,
) -> SesionEmitida:
    """Autentica una cuenta y emite su token de sesión.

    El orden es el del diseño: primero el límite de intentos (sin bcrypt ni
    cookie), después la verificación uniforme contra el hash real o el
    ficticio. El intento se registra siempre en una sesión propia, salvo
    cuando la respuesta es ``LimiteDeIntentosExcedido``, para que reintentar
    no renueve el bloqueo.
    """
    ahora = reloj()
    desde = ahora - timedelta(seconds=settings.LOGIN_VENTANA_SEGUNDOS)
    autenticado = False
    registrar_intento = True

    try:
        async with uow:
            intentos = IntentoAccesoRepository(uow.session)
            fallos = await intentos.contar_fallos_recientes(datos.email, ip, desde)
            if fallos >= settings.LOGIN_MAX_INTENTOS:
                registrar_intento = False
                mas_antiguo = await intentos.fallo_mas_antiguo(
                    datos.email, ip, desde
                )
                raise LimiteDeIntentosExcedido(_retry_after(mas_antiguo, ahora))

            usuario = await UsuarioRepository(uow.session).buscar_por_email(
                datos.email
            )
            if usuario is None:
                # Mismo costo de bcrypt que una cuenta real: no se delata la
                # existencia del correo por el tiempo de respuesta.
                await verify_password(datos.password, await hash_ficticio())
                raise CredencialesInvalidas()

            coincide = await verify_password(datos.password, usuario.password_hash)
            if not coincide or not usuario.activo:
                raise CredencialesInvalidas()

            asignaciones = await AsignacionRolRepository(uow.session).listar_vigentes(
                _clave_primaria(usuario),
                ahora,
            )
            roles = [asignacion.rol for asignacion in asignaciones]

            autenticado = True
            return SesionEmitida(
                usuario=usuario,
                token=create_access_token(payload_de_sesion(usuario, roles)),
                roles=roles,
            )
    finally:
        if registrar_intento:
            await _registrar_intento(
                session_factory,
                datos.email,
                ip,
                exito=autenticado,
                cuando=ahora,
            )


async def consultar_sesion(
    uow: UnitOfWork,
    usuario: Usuario,
    roles_token: list[str],
    *,
    reloj: Callable[[], datetime] = ahora_utc,
) -> SesionResponse:
    """Devuelve la cuenta con sus roles vigentes y los roles del token.

    Los roles que autorizan son los vigentes en la base al momento de la
    consulta; los del token se informan sin otorgar permisos.
    """
    usuario_id = _clave_primaria(usuario)
    async with uow:
        asignaciones = await AsignacionRolRepository(uow.session).listar_vigentes(
            usuario_id, reloj()
        )

    return SesionResponse(
        id=usuario_id,
        email=usuario.email,
        nombre=usuario.nombre,
        activo=usuario.activo,
        debe_cambiar_password=usuario.debe_cambiar_password,
        roles_vigentes=[asignacion.rol for asignacion in asignaciones],
        roles_token=list(roles_token),
    )


async def cambiar_password(
    uow: UnitOfWork,
    usuario: Usuario,
    datos: CambioPasswordRequest,
    *,
    reloj: Callable[[], datetime] = ahora_utc,
) -> SesionEmitida:
    """Cambia la contraseña de una cuenta ya autenticada.

    Verifica la contraseña actual antes de tocar nada, sostiene el límite de
    72 bytes aunque el schema ya lo haya validado y escribe el hash junto con
    ``password_cambiada_en`` y el evento de auditoría en la misma unidad de
    trabajo. La marca se fija con el reloj de la aplicación y el token nuevo
    se emite con ese mismo instante: así el token del propio cambio sigue
    siendo válido aunque el cambio y la emisión caigan en el mismo segundo.
    """
    if not await verify_password(datos.password_actual, usuario.password_hash):
        raise CredencialesInvalidas()

    try:
        validar_password(datos.password_nueva)
    except ValueError as error:
        raise PasswordInvalida(str(error)) from error

    ahora = reloj()
    password_hash = await hash_password(datos.password_nueva)

    async with uow:
        usuario.password_hash = password_hash
        usuario.password_cambiada_en = ahora
        usuario.debe_cambiar_password = False
        await UsuarioRepository(uow.session).flush()

        asignaciones = await AsignacionRolRepository(uow.session).listar_vigentes(
            _clave_primaria(usuario), ahora
        )
        roles = [asignacion.rol for asignacion in asignaciones]
        await EventoSeguridadRepository(uow.session).registrar(
            ACTOR_SISTEMA,
            ACCION_CAMBIO_PASSWORD,
        )

    return SesionEmitida(
        usuario=usuario,
        token=create_access_token(
            payload_de_sesion(usuario, roles),
            emitido_en=ahora,
        ),
        roles=roles,
    )
