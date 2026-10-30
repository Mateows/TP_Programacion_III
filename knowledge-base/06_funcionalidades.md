# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario** (formato US-NNN).

## Épica 1: Autenticación y acceso

### US-001 — Registro de cliente
**Como** cliente nuevo  
**Quiero** registrarme en la web  
**Para** poder acceder al sistema y consultar mis vehículos y órdenes

**Criterios de aceptación:**
- [ ] CA-1: Se crean usuario, rol CLIENTE y ficha de cliente en una sola transacción (RN-02)
- [ ] CA-2: Si el documento ya pertenece a un cliente existente, responde 409 y no se apropia de la ficha
- [ ] CA-3: Responde 201 si todo queda guardado, 422 si el cuerpo no cumple el contrato

**Reglas relacionadas**: RN-02, RN-01

### US-002 — Inicio de sesión
**Como** usuario registrado  
**Quiero** iniciar sesión con correo y contraseña  
**Para** obtener un token de acceso en una cookie HttpOnly

**Criterios de aceptación:**
- [ ] CA-1: Después de 5 intentos fallidos con el mismo correo desde la misma IP en 60 segundos, responde 429 (RN-08)
- [ ] CA-2: El cuerpo del login nunca trae el token; viaja en `Set-Cookie` con `HttpOnly`, `SameSite=Lax`, `Max-Age`
- [ ] CA-3: Responde igual y tarda igual exista o no el correo (RN-09)
- [ ] CA-4: Sin cookie o con `Authorization: Bearer`, responde 401

**Reglas relacionadas**: RN-08, RN-09

### US-003 — Cierre de sesión
**Como** usuario autenticado  
**Quiero** cerrar mi sesión  
**Para** invalidar mi cookie de acceso

**Criterios de aceptación:**
- [ ] CA-1: Borra la cookie de sesión
- [ ] CA-2: Responde 200

**Reglas relacionadas**: —

### US-004 — Consultar mi sesión actual
**Como** usuario autenticado  
**Quiero** ver mi usuario, mis roles vigentes y los que dice el token  
**Para** verificar mi estado de autenticación

**Criterios de aceptación:**
- [ ] CA-1: Responde 200 con usuario, roles vigentes y roles del token
- [ ] CA-2: Sin sesión, responde 401

**Reglas relacionadas**: RN-04

### US-005 — Cambio de contraseña
**Como** usuario autenticado  
**Quiero** cambiar mi contraseña  
**Para** mantener mi cuenta segura

**Criterios de aceptación:**
- [ ] CA-1: Las sesiones emitidas antes del cambio dejan de valer (RN-07)
- [ ] CA-2: La cookie del cambio nuevo sí vale
- [ ] CA-3: Si tengo cambio pendiente, solo puedo usar rutas de salud y `/auth` (RN-06)

**Reglas relacionadas**: RN-06, RN-07

## Épica 2: Gestión de personal y roles (solo administrador)

### US-006 — Alta de usuario de personal
**Como** administrador  
**Quiero** dar de alta un empleado con contraseña provisoria  
**Para** que pueda acceder al sistema

**Criterios de aceptación:**
- [ ] CA-1: Solo ADMIN puede crear usuarios de personal
- [ ] CA-2: Responde 201, 409 o 422

**Reglas relacionadas**: RN-01

### US-007 — Asignar y revocar roles
**Como** administrador  
**Quiero** asignar roles con vencimiento opcional y revocarlos sin borrar la fila  
**Para** controlar quién tiene acceso a qué

**Criterios de aceptación:**
- [ ] CA-1: Un usuario tiene a lo sumo una asignación abierta por rol (RN-03)
- [ ] CA-2: No puedo revocarme mi propio rol ADMIN (RN-05)
- [ ] CA-3: Reasignar un rol vencido cierra la fila anterior y abre una nueva

**Reglas relacionadas**: RN-03, RN-05

### US-008 — Consultar eventos de seguridad
**Como** administrador  
**Quiero** ver el historial de seguridad paginado  
**Para** auditar cambios de rol, contraseña y altas

**Criterios de aceptación:**
- [ ] CA-1: Solo ADMIN puede ver eventos
- [ ] CA-2: Responde 200 o 422

**Reglas relacionadas**: —

## Épica 3: Clientes y vehículos

### US-009 — Alta de cliente
**Como** recepción o administrador  
**Quiero** dar de alta un cliente  
**Para** registrarlo en el taller

**Criterios de aceptación:**
- [ ] CA-1: Solo RECEPCION o ADMIN
- [ ] CA-2: Documento único (RN-01)
- [ ] CA-3: Responde 201, 409 o 422

**Reglas relacionadas**: RN-01

### US-010 — Consulta de cliente con vehículos
**Como** recepción o administrador  
**Quiero** ver un cliente y sus vehículos  
**Para** gestionar su información

**Criterios de aceptación:**
- [ ] CA-1: Responde 200 o 404

**Reglas relacionadas**: —

### US-011 — Alta de vehículo para un cliente
**Como** recepción o administrador  
**Quiero** registrar un vehículo para un cliente  
**Para** asociarlo a órdenes futuras

**Criterios de aceptación:**
- [ ] CA-1: Patente única entre vigentes (RN-01)
- [ ] CA-2: Año entre 1950 y 2100
- [ ] CA-3: Responde 201, 404, 409 o 422

**Reglas relacionadas**: RN-01

### US-012 — Baja lógica de vehículo
**Como** recepción o administrador  
**Quiero** dar de baja un vehículo vendido  
**Para** que no aparezca en listados pero se conserven sus órdenes

**Criterios de aceptación:**
- [ ] CA-1: Un vehículo con órdenes abiertas no se da de baja (RN-16)
- [ ] CA-2: Responde 204, 404 o 409
- [ ] CA-3: El comprador puede registrarlo con la misma patente (índice único parcial)

**Reglas relacionadas**: RN-16

### US-013 — Ver mis vehículos (cliente)
**Como** cliente autenticado  
**Quiero** ver mis propios vehículos  
**Para** consultar su información

**Criterios de aceptación:**
- [ ] CA-1: Solo ve sus propios vehículos, no los ajenos (RN-17)
- [ ] CA-2: Responde 200 o 403

**Reglas relacionadas**: RN-17

## Épica 4: Repuestos y stock

### US-014 — Listar repuestos
**Como** personal del taller  
**Quiero** listar repuestos con búsqueda y paginación  
**Para** encontrar repuestos disponibles

**Criterios de aceptación:**
- [ ] CA-1: Búsqueda por descripción con parámetros ligados
- [ ] CA-2: Página empieza en 1, size de 1 a 100 (default 20)
- [ ] CA-3: Página más allá de la última da 422
- [ ] CA-4: Solo ADMIN, RECEPCION, MECANICO

**Reglas relacionadas**: —

### US-015 — Alta de repuesto con stock inicial
**Como** administrador  
**Quiero** dar de alta un repuesto con su stock inicial  
**Para** tenerlo en inventario

**Criterios de aceptación:**
- [ ] CA-1: Código único entre vigentes (RN-01)
- [ ] CA-2: Precio > 0, stock >= 0
- [ ] CA-3: El stock inicial se registra como un movimiento (RN-14)
- [ ] CA-4: Responde 201, 409 o 422

**Reglas relacionadas**: RN-01, RN-14

### US-016 — Editar repuesto
**Como** administrador  
**Quiero** editar descripción y precio de un repuesto  
**Para** mantener el catálogo actualizado

**Criterios de aceptación:**
- [ ] CA-1: PATCH aplicado solo a los campos enviados (`exclude_unset`)
- [ ] CA-2: Si cambia el precio, deja línea en `historial_precio_repuesto` en la misma transacción (RN-20)
- [ ] CA-3: Si no cambia el precio, no deja línea de historial
- [ ] CA-4: No se puede editar el stock por PATCH (RN-14)

**Reglas relacionadas**: RN-14, RN-20

### US-017 — Reponer stock
**Como** administrador  
**Quiero** reponer el stock de un repuesto  
**Para** mantener el inventario

**Criterios de aceptación:**
- [ ] CA-1: Se registra un movimiento de stock (RN-14)
- [ ] CA-2: Responde 200, 404 o 422

**Reglas relacionadas**: RN-14

### US-018 — Ver movimientos y precios de un repuesto
**Como** administrador  
**Quiero** ver los movimientos de stock y el historial de precios de un repuesto  
**Para** auditar cambios

**Criterios de aceptación:**
- [ ] CA-1: Solo ADMIN
- [ ] CA-2: Responde 200 o 404

**Reglas relacionadas**: —

## Épica 5: Órdenes de trabajo

### US-019 — Apertura de orden de trabajo
**Como** recepción o administrador  
**Quiero** abrir una orden con ítems de repuestos  
**Para** registrar una reparación

**Criterios de aceptación:**
- [ ] CA-1: Nace PENDIENTE con al menos un ítem (RN-10)
- [ ] CA-2: No hay repuestos repetidos en la orden (UNIQUE orden_id + repuesto_id)
- [ ] CA-3: Precio de cada ítem copiado del repuesto; total calculado por el servidor (RN-10)
- [ ] CA-4: Precio y total no viajan en el cuerpo de la request
- [ ] CA-5: Responde 201 con precios copiados, total e historial; 409 si hay un repuesto inexistente

**Reglas relacionadas**: RN-10, RN-19

### US-020 — Listar órdenes
**Como** personal del taller  
**Quiero** listar órdenes filtradas por estado  
**Para** ver el estado del taller

**Criterios de aceptación:**
- [ ] CA-1: Filtro por estado, paginación
- [ ] CA-2: Solo ADMIN, RECEPCION, MECANICO
- [ ] CA-3: Responde 200 o 422

**Reglas relacionadas**: —

### US-021 — Ver detalle de orden
**Como** personal o dueño del vehículo  
**Quiero** ver el detalle de una orden con vehículo, cliente, ítems, repuestos e historial  
**Para** conocer el estado de la reparación

**Criterios de aceptación:**
- [ ] CA-1: El cliente solo ve sus propias órdenes (RN-17)
- [ ] CA-2: Carga anticipada en el repositorio (sin N+1)
- [ ] CA-3: Responde 200, 403 o 404

**Reglas relacionadas**: RN-17

### US-022 — Iniciar orden
**Como** mecánico  
**Quiero** iniciar una orden PENDIENTE  
**Para** comenzar la reparación

**Criterios de aceptación:**
- [ ] CA-1: Solo MECANICO
- [ ] CA-2: Queda asignado a mí
- [ ] CA-3: Transición PENDIENTE → EN_REPARACION (RN-11)
- [ ] CA-4: Responde 200, 404 o 409

**Reglas relacionadas**: RN-11

### US-023 — Terminar orden
**Como** mecánico asignado o administrador  
**Quiero** terminar una orden  
**Para** descontar el stock de los repuestos usados

**Criterios de aceptación:**
- [ ] CA-1: Transición EN_REPARACION → TERMINADA (RN-11)
- [ ] CA-2: Descuenta el stock de cada ítem, deja un movimiento por salida y una línea de historial (RN-13)
- [ ] CA-3: Todo en una sola transacción (Unit of Work); si un repuesto no alcanza, no queda ninguna escritura (RN-13)
- [ ] CA-4: Responde 200, 403, 404 o 409

**Reglas relacionadas**: RN-11, RN-13

### US-024 — Cancelar orden
**Como** recepción, administrador o dueño del vehículo  
**Quiero** cancelar una orden pendiente  
**Para** anular una reparación

**Criterios de aceptación:**
- [ ] CA-1: El dueño del vehículo puede cancelar aunque no tenga rol de personal
- [ ] CA-2: El permiso se evalúa antes que el estado (403 antes que 409) (RN-12)
- [ ] CA-3: Solo se puede cancelar desde PENDIENTE (RN-11)
- [ ] CA-4: Responde 200, 403, 404 o 409

**Reglas relacionadas**: RN-11, RN-12

### US-025 — Ver mis órdenes (cliente)
**Como** cliente autenticado  
**Quiero** ver mis órdenes  
**Para** consultar el estado de mis reparaciones

**Criterios de aceptación:**
- [ ] CA-1: Solo ve sus propias órdenes (RN-17)
- [ ] CA-2: Paginación
- [ ] CA-3: Responde 200 o 422

**Reglas relacionadas**: RN-17

### US-026 — Consultar catálogo de estados
**Como** usuario autenticado  
**Quiero** ver los estados posibles de una orden  
**Para** saber en qué estado puede estar una orden

**Criterios de aceptación:**
- [ ] CA-1: Los cuatro estados por posición, con TERMINADA y CANCELADA marcadas como finales
- [ ] CA-2: Sin sesión, responde 401
- [ ] CA-3: Estado no declarado da 422

**Reglas relacionadas**: RN-19

## Épica 6: Salud del sistema

### US-027 — Health check vivo
**Como** cualquier cliente o sistema externo  
**Quiero** saber si la API está viva  
**Para** monitorear disponibilidad

**Criterios de aceptación:**
- [ ] CA-1: No toca la base de datos
- [ ] CA-2: Responde 200

**Reglas relacionadas**: —

### US-028 — Health check listo
**Como** cualquier cliente o sistema externo  
**Quiero** saber si la API puede atender peticiones  
**Para** monitorear disponibilidad real

**Criterios de aceptación:**
- [ ] CA-1: Ejecuta `SELECT 1` contra la base
- [ ] CA-2: Responde 200 si la base contesta, 503 si no

**Reglas relacionadas**: —
