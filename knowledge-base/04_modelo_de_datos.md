# Modelo de Datos

## Dominios

- **Usuarios y autenticación**: cuentas de acceso, roles, intentos de acceso, eventos de seguridad.
- **Clientes y vehículos**: fichas de cliente, vehículos asociados, borrado lógico de vehículos.
- **Repuestos e inventario**: catálogo de repuestos, stock, movimientos de stock, historial de precios.
- **Órdenes de trabajo**: órdenes, ítems de repuesto, estados de orden (catálogo), historial de cambios de estado.

## ERD (Entity Relationship Diagram)

```
usuario 1 —< asignacion_rol >—1 rol (catálogo implícito vía CHECK)
usuario 1 —1 cliente (opcional, usuario_id UNIQUE y nulo permitido)
cliente 1 —< vehiculo (borrado lógico, índice único parcial de patente vigente)
vehiculo 1 —< orden_trabajo
orden_trabajo N —1 estado_orden (catálogo, clave foránea)
orden_trabajo 1 —< item_orden (composición: ítem no existe sin orden)
item_orden N —1 repuesto
repuesto 1 —< movimiento_stock
repuesto 1 —< historial_precio_repuesto
orden_trabajo 1 —< historial_estado_orden
orden_trabajo 1 —< movimiento_stock (opcional)
usuario 1 —< historial_estado_orden (quien hizo el cambio)
usuario 1 —< movimiento_stock (quien hizo el movimiento)
usuario 1 —< historial_precio_repuesto (quien cambió el precio)
usuario 1 —< intento_acceso (email, no FK directa)
```

## Entidades

### usuario
- Atributos: `id` (PK), `email` (UNIQUE), `nombre`, `password_hash`, `activo`, `debe_cambiar_password`, `password_cambiada_en` (timestamptz, nulo permitido)
- Relaciones: `cliente` (uno a uno opcional, returns object not list), `asignacion_rol` (uno a muchos)
- Constraints: `email UNIQUE`
- Índices: PK por `id`

### asignacion_rol
- Atributos: `id` (PK), `usuario_id`, `rol` (CHECK: ADMIN, RECEPCION, MECANICO, CLIENTE), `desde`, `vence_en` (nulo), `revocada_en` (nulo), `otorgada_por` (nulo)
- Constraints: índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`
- Relaciones: `usuario` (muchos a uno)

### intento_acceso
- Atributos: `id` (PK), `cuando`, `email`, `ip`, `exito`
- Índices: `(email, ip, cuando)`

### evento_seguridad
- Atributos: `id` (PK), `cuando`, `actor` (texto, no es usuario), `accion`
- Sin restricciones extra

### cliente
- Atributos: `id` (PK), `usuario_id` (nulo permitido, UNIQUE), `nombre`, `documento` (UNIQUE), `telefono`
- Relaciones: `usuario` (uno a uno opcional), `vehiculo` (uno a muchos)

### vehiculo
- Atributos: `id` (PK), `cliente_id`, `patente`, `marca`, `modelo`, `anio`, `borrado_en` (nulo)
- Constraints: índice único parcial `(patente) WHERE borrado_en IS NULL`; `CHECK anio BETWEEN 1950 AND 2100`
- Relaciones: `cliente` (muchos a uno), `orden_trabajo` (uno a muchos)

### repuesto
- Atributos: `id` (PK), `codigo`, `descripcion`, `precio` (NUMERIC 10,2), `stock`, `borrado_en` (nulo)
- Constraints: índice único parcial `(codigo) WHERE borrado_en IS NULL`; `CHECK precio > 0`; `CHECK stock >= 0`
- Relaciones: `item_orden` (uno a muchos), `movimiento_stock` (uno a muchos), `historial_precio_repuesto` (uno a muchos)

### estado_orden (catálogo)
- Atributos: `codigo` (PK, no es `id`), `descripcion`, `posicion` (UNIQUE), `es_final`
- Relaciones: `orden_trabajo` (uno a muchos), `historial_estado_orden` (uno a muchos)
- Nota: tabla de referencia cargada por `seed.py`; la API solo lee, no escribe

### orden_trabajo
- Atributos: `id` (PK), `vehiculo_id`, `mecanico_id` (nulo), `estado` (FK a estado_orden.codigo), `falla`, `creada_en`, `total` (NUMERIC 12,2)
- Constraints: `estado` es clave foránea a `estado_orden.codigo`; `CHECK total >= 0`
- Relaciones: `vehiculo` (muchos a uno), `mecanico` (usuario, muchos a uno), `item_orden` (uno a muchos), `historial_estado_orden` (uno a muchos), `movimiento_stock` (uno a muchos)

### item_orden
- Atributos: `id` (PK), `orden_id`, `repuesto_id`, `cantidad`, `precio_unitario` (NUMERIC 10,2)
- Constraints: `CHECK cantidad > 0`; `CHECK precio_unitario > 0`; `UNIQUE (orden_id, repuesto_id)`
- Relaciones: `orden_trabajo` (muchos a uno), `repuesto` (muchos a uno)

### historial_estado_orden (sólo agregado)
- Atributos: `id` (PK), `orden_id`, `desde_estado` (nulo, FK a estado_orden.codigo), `hasta_estado` (FK a estado_orden.codigo), `usuario_id`, `cuando`
- Constraints: sólo agregado (disparador rechaza UPDATE/DELETE)
- Relaciones: `orden_trabajo`, `estado_orden` (dos veces), `usuario`

### movimiento_stock (sólo agregado)
- Atributos: `id` (PK), `repuesto_id`, `orden_id` (nulo), `usuario_id`, `cantidad`, `motivo`, `cuando`
- Constraints: `CHECK cantidad > 0`; sólo agregado
- Relaciones: `repuesto`, `orden_trabajo` (opcional), `usuario`

### historial_precio_repuesto (sólo agregado)
- Atributos: `id` (PK), `repuesto_id`, `usuario_id`, `precio_anterior` (NUMERIC 10,2), `precio_nuevo` (NUMERIC 10,2), `cuando`
- Constraints: `CHECK precio_nuevo > 0`; `CHECK precio_nuevo > precio_anterior`; sólo agregado
- Relaciones: `repuesto`, `usuario`

## Reglas generales de modelo

- Todas las fechas son `timestamptz`.
- El dinero es `NUMERIC` y en Python `Decimal`, nunca `float`.
- Cada clave foránea lleva un índice explícito (PostgreSQL no lo crea solo).
- LA PATENTE Y EL CÓDIGO NO SON UNIQUE comunes: usan índice único parcial con `WHERE borrado_en IS NULL`.
- `usuario.rol` no existe como columna; los roles son filas de `asignacion_rol` vigentes.

## Seed data inicial

- **Catálogo de estados**: PENDIENTE (posición 1), EN_REPARACION (2), TERMINADA (3, final), CANCELADA (4, final), cada uno con su descripción. Cargado primero porque todo lo que tiene un estado apunta a él.
- **Usuarios**: admin@example.com y admin2@example.com (ADMIN), recepcion@example.com (RECEPCION), mecanico@example.com y mecanico2@example.com (MECANICO), cliente@example.com (CLIENTE), nuevo@example.com (MECANICO con cambio de contraseña obligatorio).
- **Clientes**: Laura (con usuario cliente@example.com, dos vehículos); Jorge (sin usuario, un vehículo).
- **Repuestos**: Filtro de aceite (stock 10), pastillas de freno (4), bujía (2), aceite por litro (20). Cada stock cargado como movimiento "Stock inicial".
- **Órdenes**: La 1 (PENDIENTE, primer vehículo de Laura); La 2 (EN_REPARACION, vehículo de Jorge, asignada a mecanico@example.com, con 4 bujías cuando hay 2).
- **Historial de precios**: una línea del filtro de aceite: de 8000 a 8500.
- **Historial de seguridad**: una línea con actor SISTEMA: "Carga de los datos iniciales".
