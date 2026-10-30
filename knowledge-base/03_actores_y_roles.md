# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|-------|-------------|-----------------|
| Recepción | Empleado del taller que da de alta clientes, vehículos y abre órdenes de trabajo | Endpoints protegidos con rol RECEPCION o ADMIN |
| Mecánico | Empleado que inicia órdenes PENDIENTE y termina órdenes EN_REPARACION únicamente cuando está asignado como mecánico de la orden (descuenta stock al terminar) | Endpoints protegidos con rol MECANICO |
| Administrador | Gestiona catálogo de repuestos, stock, personal y roles | Endpoints protegidos con rol ADMIN |
| Cliente | Persona que se registra por la web y consulta estado de sus vehículos y órdenes | Endpoints de "lo propio" (`/mis-*`), autenticado |
| Sistema (SISTEMA) | Actor textual, no un usuario de base. Registra altas, cambios de rol y de contraseña en historial de seguridad | No autenticado; escribe en `evento_seguridad` |

## RBAC — Matriz de permisos

| Rol | Recurso | Permisos |
|-----|---------|----------|
| ADMIN | Usuarios y roles | Alta, consulta, asignación, revocación |
| ADMIN | Eventos de seguridad | Consulta paginada |
| ADMIN, RECEPCION | Clientes | Alta, consulta con vehículos, baja de vehículos |
| ADMIN, RECEPCION | Órdenes | Crear órdenes |
| ADMIN, RECEPCION, MECANICO | Órdenes | Listar órdenes |
| ADMIN, RECEPCION, dueño del vehículo | Órdenes | Cancelar órdenes PENDIENTE (el dueño cancela sin rol de personal; la ruta no usa `requiere_rol` genérica; el permiso se evalúa antes que el estado) |
| ADMIN, RECEPCION, MECANICO | Repuestos (consulta) | Sólo pueden consultar/listar repuestos |
| ADMIN | Repuestos (administración) | Crear repuestos, editar descripción y precio, dar de baja repuestos, reponer stock, consultar movimientos de stock, consultar historial de precios |
| MECANICO | Órdenes | Iniciar órdenes PENDIENTE (queda asignado como mecánico de la orden) |
| MECANICO asignado, ADMIN | Órdenes | Terminar órdenes EN_REPARACION |
| Personal autorizado, dueño del vehículo | Órdenes | Ver detalle de orden (según reglas de autorización correspondientes) |
| Cliente (autenticado) | Mis vehículos | Consulta |
| Cliente (autenticado) | Mis órdenes | Consulta |
| Cualquier actor | Salud (`/health/*`) | Consulta sin autenticación |
| Cualquier actor | Auth (registro, login, logout) | Registro, inicio y cierre de sesión sin autenticación previa |
| Usuario autenticado | Auth (yo, cambiar-password) | Consultar sesión propia y cambiar contraseña; requiere sesión válida, sin rol específico |

**Nota importante:** Los roles viven en su propia tabla (`asignacion_rol`). `usuario` no tiene columna `rol`. Los roles vigentes se consultan en la base en cada petición; los roles que trae el token son informativos. Revocar un rol quita el permiso a una sesión ya abierta, sin esperar a que el token venza.

## Rutas de salud y autenticación

### Sin autenticación

- `GET /health/live`
- `GET /health/ready`
- `POST /auth/registro`
- `POST /auth/login`
- `POST /auth/logout`

### Autenticadas, sin rol específico

- `GET /auth/yo`
- `POST /auth/cambiar-password`

**Aclaraciones:**

- `POST /auth/cambiar-password` requiere una sesión válida.
- No requiere un rol específico.
- Puede ser utilizada por un usuario que tiene cambio obligatorio de contraseña pendiente.
- Un usuario con cambio pendiente sólo puede acceder a salud y autenticación, pero eso no elimina la necesidad de autenticarse para cambiar la contraseña.
