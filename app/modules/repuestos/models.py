"""Modelos de tabla del módulo de repuestos.

``repuesto`` es la ficha del catálogo y usa baja lógica: el código es único
**sólo entre los vigentes** mediante un índice único parcial, para que un
repuesto dado de baja libere su código. ``movimiento_stock`` e
``historial_precio_repuesto`` son de sólo agregado: cada cambio de stock o de
precio deja una fila inmutable con su actor y su momento.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, DateTime, Index, Numeric, func, text
from sqlmodel import Field, SQLModel


class Repuesto(SQLModel, table=True):
    """Repuesto del catálogo, con precio positivo y stock no negativo."""

    __tablename__ = "repuesto"
    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_repuesto_precio"),
        CheckConstraint("stock >= 0", name="ck_repuesto_stock"),
        Index(
            "ix_repuesto_codigo_vigente",
            "codigo",
            unique=True,
            postgresql_where=text("borrado_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=50, nullable=False)
    descripcion: str = Field(max_length=200, nullable=False)
    precio: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    stock: int = Field(nullable=False)
    borrado_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class MovimientoStock(SQLModel, table=True):
    """Variación del stock de un repuesto, de sólo agregado.

    ``orden_id`` referencia la tabla de órdenes de trabajo, que llega en C-07:
    C-06 declara la columna pero nunca la escribe.
    """

    __tablename__ = "movimiento_stock"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_movimiento_stock_cantidad"),
    )

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True, nullable=False)
    orden_id: int | None = Field(
        default=None,
        foreign_key="orden_trabajo.id",
        index=True,
        nullable=True,
    )
    usuario_id: int = Field(foreign_key="usuario.id", index=True, nullable=False)
    cantidad: int = Field(nullable=False)
    motivo: str = Field(max_length=100, nullable=False)
    cuando: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


class HistorialPrecioRepuesto(SQLModel, table=True):
    """Línea de historial de un cambio efectivo de precio, de sólo agregado.

    El precio sólo aumenta: el ``CHECK`` ``precio_nuevo > precio_anterior`` es
    la última red detrás del servicio.
    """

    __tablename__ = "historial_precio_repuesto"
    __table_args__ = (
        CheckConstraint(
            "precio_nuevo > 0",
            name="ck_historial_precio_nuevo_positivo",
        ),
        CheckConstraint(
            "precio_nuevo > precio_anterior",
            name="ck_historial_precio_aumenta",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True, nullable=False)
    usuario_id: int = Field(foreign_key="usuario.id", index=True, nullable=False)
    precio_anterior: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    precio_nuevo: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    cuando: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
