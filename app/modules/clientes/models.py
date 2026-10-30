"""Modelos de tabla del módulo de clientes.

``cliente`` es la ficha del taller: puede existir sin cuenta de usuario
(``usuario_id`` nulo) y el documento es único. ``vehiculo`` pertenece siempre a
un cliente y usa baja lógica: la patente es única **sólo entre los vigentes**
mediante un índice único parcial, para que un vehículo dado de baja libere su
patente.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Index, text
from sqlmodel import Field, SQLModel


class Cliente(SQLModel, table=True):
    """Ficha de un cliente del taller, con o sin cuenta asociada."""

    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int | None = Field(
        default=None,
        foreign_key="usuario.id",
        index=True,
        unique=True,
        nullable=True,
    )
    nombre: str = Field(max_length=150, nullable=False)
    documento: str = Field(max_length=50, unique=True, nullable=False)
    telefono: str | None = Field(default=None, max_length=30, nullable=True)


class Vehiculo(SQLModel, table=True):
    """Vehículo asociado a un cliente, con baja lógica y año acotado."""

    __tablename__ = "vehiculo"
    __table_args__ = (
        CheckConstraint("anio BETWEEN 1950 AND 2100", name="ck_vehiculo_anio"),
        Index(
            "ix_vehiculo_patente_vigente",
            "patente",
            unique=True,
            postgresql_where=text("borrado_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True, nullable=False)
    patente: str = Field(max_length=10, nullable=False)
    marca: str = Field(max_length=100, nullable=False)
    modelo: str = Field(max_length=100, nullable=False)
    anio: int = Field(nullable=False)
    borrado_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
