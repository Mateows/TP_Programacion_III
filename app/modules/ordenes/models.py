"""Modelos de tabla del módulo de órdenes de trabajo.

``estado_orden`` es el catálogo de estados del ciclo de vida. ``orden_trabajo``
es la orden en sí, ``item_orden`` los repuestos pedidos con su precio copiado y
``historial_estado_orden`` el registro inmutable de cada transición. No se
declaran ``Relationship``: las lecturas usan ``JOIN`` explícitos por clave
foránea como estrategia de carga anticipada, sin cargas perezosas.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlmodel import Field, SQLModel


class EstadoOrden(SQLModel, table=True):
    """Estado del ciclo de vida de una orden, identificado por su código.

    Es un catálogo de referencia: lo carga ``seed.py`` y la API solo lo lee.
    La clave primaria es ``codigo`` porque la FK de ``orden_trabajo.estado``
    apunta al nombre del estado, no a un identificador numérico.
    """

    __tablename__ = "estado_orden"

    codigo: str = Field(max_length=30, primary_key=True)
    descripcion: str = Field(max_length=255, nullable=False)
    posicion: int = Field(unique=True, nullable=False)
    es_final: bool = Field(default=False, nullable=False)


class OrdenTrabajo(SQLModel, table=True):
    """Orden de trabajo de un vehículo, con su mecánico y su estado actual.

    ``total`` se congela al crear la orden a partir de los precios copiados en
    sus ítems. ``creada_en`` la fija la base y no hay marca de actualización:
    la orden es de sólo agregado y su ciclo se sigue por el historial.
    """

    __tablename__ = "orden_trabajo"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_orden_trabajo_total"),
    )

    id: int | None = Field(default=None, primary_key=True)
    vehiculo_id: int = Field(foreign_key="vehiculo.id", index=True, nullable=False)
    mecanico_id: int | None = Field(
        default=None,
        foreign_key="usuario.id",
        index=True,
        nullable=True,
    )
    estado: str = Field(
        foreign_key="estado_orden.codigo",
        max_length=30,
        index=True,
        nullable=False,
    )
    falla: str = Field(max_length=500, nullable=False)
    total: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    creada_en: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


class ItemOrden(SQLModel, table=True):
    """Repuesto pedido en una orden, con el precio congelado al momento del alta.

    El ``UniqueConstraint`` impide repetir el mismo repuesto en la orden; la
    validación del contrato lo rechaza antes con ``422`` y la base queda como
    última red.
    """

    __tablename__ = "item_orden"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_item_orden_cantidad"),
        CheckConstraint("precio_unitario > 0", name="ck_item_orden_precio"),
        UniqueConstraint(
            "orden_id",
            "repuesto_id",
            name="uq_item_orden_repuesto",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True, nullable=False)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True, nullable=False)
    cantidad: int = Field(nullable=False)
    precio_unitario: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False),
    )


class HistorialEstadoOrden(SQLModel, table=True):
    """Línea inmutable de una transición de estado de la orden.

    ``desde_estado`` es nulo sólo en la línea de alta, cuando la orden todavía
    no tenía estado previo. ``cuando`` lo fija la base y no hay marcas de
    auditoría adicionales: el historial es de sólo agregado.
    """

    __tablename__ = "historial_estado_orden"

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True, nullable=False)
    desde_estado: str | None = Field(
        default=None,
        foreign_key="estado_orden.codigo",
        max_length=30,
        index=True,
        nullable=True,
    )
    hasta_estado: str = Field(
        foreign_key="estado_orden.codigo",
        max_length=30,
        index=True,
        nullable=False,
    )
    usuario_id: int = Field(foreign_key="usuario.id", index=True, nullable=False)
    cuando: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
