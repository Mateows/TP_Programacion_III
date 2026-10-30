"""Vocabulario de los motivos de movimiento de stock.

Los motivos son texto en la base, sin enum ni columna de tipo. Las constantes
compartidas evitan que C-06 y C-07 escriban valores divergentes para el mismo
hecho de negocio: el consumo por orden lo registra C-07 al terminarla.
"""

MOTIVO_STOCK_INICIAL = "Stock inicial"
MOTIVO_REPOSICION = "Reposición"
MOTIVO_CONSUMO_ORDEN = "Consumo por orden"

__all__ = ["MOTIVO_STOCK_INICIAL", "MOTIVO_REPOSICION", "MOTIVO_CONSUMO_ORDEN"]
