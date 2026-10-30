"""Repositorios del módulo de autenticación.

Cada repositorio atiende una tabla de C-02 y hereda de ``BaseRepository``:
envía los cambios con ``flush()`` y nunca confirma, porque la confirmación es
responsabilidad de la ``UnitOfWork``. Las consultas del límite de intentos
usan el índice ``ix_intento_acceso_email_ip_cuando``.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import ScalarSelect, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)


class UsuarioRepository(BaseRepository[Usuario]):
    """Cuentas de acceso del taller."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Usuario)

    async def buscar_por_email(self, email: str) -> Usuario | None:
        """Devuelve la cuenta con ese correo, o ``None`` si no existe.

        El correo es único en ``usuario``, así que la consulta devuelve a lo
        sumo una fila.
        """
        return await self._primero(self._sentencia().where(Usuario.email == email))


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    """Asignaciones de rol con su vigencia y revocación."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AsignacionRol)

    async def listar_vigentes(
        self,
        usuario_id: int,
        ahora: datetime,
    ) -> list[AsignacionRol]:
        """Lista las asignaciones vigentes del usuario en el instante dado.

        Una asignación está vigente cuando no fue revocada y su vencimiento,
        si existe, es posterior a ``ahora``. Es la fuente de permisos de cada
        petición: los roles del token son solo informativos.
        """
        return await self.list(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.revocada_en.is_(None),
            or_(
                AsignacionRol.vence_en.is_(None),
                AsignacionRol.vence_en > ahora,
            ),
        )

    async def buscar_abierta(
        self,
        usuario_id: int,
        rol: str,
    ) -> AsignacionRol | None:
        """Devuelve la asignación abierta del usuario para ese rol.

        "Abierta" significa sin marca de revocación, sin importar el
        vencimiento: una asignación vencida sigue ocupando el lugar único del
        rol y el servicio debe revocarla antes de insertar la nueva. El índice
        único parcial solo excluye las revocadas, no las vencidas.
        """
        return await self._primero(
            self._sentencia().where(
                AsignacionRol.usuario_id == usuario_id,
                AsignacionRol.rol == rol,
                AsignacionRol.revocada_en.is_(None),
            )
        )

    async def listar_historial(self, usuario_id: int) -> list[AsignacionRol]:
        """Devuelve todas las asignaciones del usuario, abiertas o no.

        Incluye revocadas y vencidas porque el endpoint sirve para auditar: el
        estado se lee en ``vence_en`` y ``revocada_en``. El desempate por
        ``id`` mantiene el orden estable cuando dos asignaciones comparten
        marca de inicio.
        """
        sentencia = (
            self._sentencia()
            .where(AsignacionRol.usuario_id == usuario_id)
            .order_by(AsignacionRol.desde.desc(), AsignacionRol.id.desc())
        )
        resultado = await self._session.scalars(sentencia)
        return [fila for fila in resultado.all()]

    async def contar_admin_vigentes(self, ahora: datetime, *, excluir_id: int) -> int:
        """Cuenta administradores vigentes distintos de la asignación indicada.

        Una asignación ``ADMIN`` es vigente cuando no está revocada, su
        vencimiento no es anterior a ``ahora`` y su cuenta está activa: una
        cuenta inactiva no puede autenticarse, así que su rol no evita que el
        sistema quede sin administración.
        """
        sentencia = (
            select(func.count())
            .select_from(AsignacionRol)
            .join(Usuario, AsignacionRol.usuario_id == Usuario.id)
            .where(
                AsignacionRol.rol == "ADMIN",
                AsignacionRol.revocada_en.is_(None),
                or_(
                    AsignacionRol.vence_en.is_(None),
                    AsignacionRol.vence_en > ahora,
                ),
                Usuario.activo.is_(True),
                AsignacionRol.id != excluir_id,
            )
        )
        resultado = await self._session.scalars(sentencia)
        return int(resultado.first() or 0)


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    """Intentos de acceso usados por el límite de intentos fallidos."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IntentoAcceso)

    async def _escalar(self, sentencia: Select[Any]) -> Any:
        """Ejecuta una sentencia de agregación y devuelve su único valor."""
        resultado = await self._session.scalars(sentencia)
        return resultado.first()

    def _ultimo_exito(
        self,
        email: str,
        ip: str,
    ) -> ScalarSelect[Any]:
        """Subconsulta con la marca del último acceso exitoso de correo e IP.

        Se desactiva la correlación automática para que la subconsulta tenga
        su propio ``FROM``: el máximo se calcula sobre toda la tabla, no sobre
        las filas que el conteo ya filtró.
        """
        return (
            select(func.max(IntentoAcceso.cuando))
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .correlate(None)
            .scalar_subquery()
        )

    async def contar_fallos_recientes(
        self,
        email: str,
        ip: str,
        desde: datetime,
    ) -> int:
        """Cuenta los fallos posteriores al último éxito dentro de la ventana.

        Solo se cuentan los fallos de ese correo y esa dirección ocurridos en
        o después de ``desde`` y posteriores al último inicio de sesión
        exitoso: un éxito reinicia el conteo sin borrar los registros.
        """
        ultimo_exito = self._ultimo_exito(email, ip)
        sentencia = (
            select(func.count())
            .select_from(IntentoAcceso)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(False),
                IntentoAcceso.cuando >= desde,
                or_(ultimo_exito.is_(None), IntentoAcceso.cuando > ultimo_exito),
            )
        )

        total = await self._escalar(sentencia)
        return int(total or 0)

    async def fallo_mas_antiguo(
        self,
        email: str,
        ip: str,
        desde: datetime,
    ) -> datetime | None:
        """Devuelve la marca del fallo más antiguo que todavía cuenta.

        Se usa para calcular ``Retry-After``: el bloqueo se libera cuando ese
        fallo sale de la ventana. Aplica el mismo filtro que el conteo, así
        que los fallos anteriores al último éxito no cuentan.
        """
        ultimo_exito = self._ultimo_exito(email, ip)
        sentencia = select(func.min(IntentoAcceso.cuando)).where(
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
            IntentoAcceso.cuando >= desde,
            or_(ultimo_exito.is_(None), IntentoAcceso.cuando > ultimo_exito),
        )

        marca = await self._escalar(sentencia)
        return marca if isinstance(marca, datetime) else None

    async def ultimo_exito(
        self,
        email: str,
        ip: str,
        desde: datetime,
    ) -> datetime | None:
        """Devuelve la marca del último éxito de ese correo y dirección.

        Solo considera éxitos ocurridos en o después de ``desde``: un éxito
        más antiguo que la ventana no puede reiniciar el conteo de fallos que
        sí están dentro de ella.
        """
        sentencia = select(func.max(IntentoAcceso.cuando)).where(
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(True),
            IntentoAcceso.cuando >= desde,
        )

        marca = await self._escalar(sentencia)
        return marca if isinstance(marca, datetime) else None

    async def registrar(
        self,
        email: str,
        ip: str,
        *,
        exito: bool,
        cuando: datetime | None = None,
    ) -> IntentoAcceso:
        """Agrega el intento a la sesión y hace ``flush`` sin confirmar.

        Sin ``cuando`` explícito, la marca la resuelve el ``server_default``
        de la base. El intento es un registro de auditoría: se conserva aunque
        la cuenta cambie o se dé de baja.
        """
        intento = IntentoAcceso(email=email, ip=ip, exito=exito)
        if cuando is not None:
            intento.cuando = cuando
        return await self.add(intento)


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    """Eventos auditables de la cuenta, con actor textual."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EventoSeguridad)

    async def registrar(self, actor: str, accion: str) -> EventoSeguridad:
        """Agrega el evento y hace ``flush`` sin confirmar.

        El actor puede ser ``SISTEMA``; el evento no referencia la cuenta para
        sobrevivir a su modificación o baja.
        """
        return await self.add(EventoSeguridad(actor=actor, accion=accion))

    async def listar_paginado(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[EventoSeguridad]:
        """Devuelve una página del historial, del evento más reciente al más viejo.

        El desempate por ``id`` es obligatorio: sin él, dos eventos con la
        misma marca temporal podrían repetirse u omitirse entre páginas. El
        total de filas lo resuelve ``contar()`` del repositorio base.
        """
        sentencia = (
            self._sentencia()
            .order_by(EventoSeguridad.cuando.desc(), EventoSeguridad.id.desc())
            .limit(limit)
            .offset(offset)
        )
        resultado = await self._session.scalars(sentencia)
        return [evento for evento in resultado.all()]
