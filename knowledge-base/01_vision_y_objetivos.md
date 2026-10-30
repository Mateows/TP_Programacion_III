# Visión y Objetivos

## Propósito del sistema

Proveer una API backend pura para un taller mecánico que gestione su operación diaria: alta de clientes y vehículos, apertura de órdenes de trabajo con ítems de repuestos, descuento atómico de stock al terminar reparaciones, y consulta de estado por parte de los clientes. Todo con autenticación (bcrypt + JWT en cookie HttpOnly), autorización por roles consultados en la base de datos en cada petición, y transacciones atómicas mediante el patrón Unit of Work.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|-------|-------------------|----------------------|
| Recepción | Abrir órdenes de trabajo para vehículos ingresados | Alta de clientes y vehículos; consulta de órdenes |
| Mecánico | Iniciar y terminar órdenes de reparación | Descontar stock de repuestos usados al terminar |
| Administrador | Mantener el catálogo de repuestos, stock y personal | Gestionar roles de usuarios con vencimiento; revisar eventos de seguridad |
| Cliente | Registrarse y consultar el estado de sus vehículos y órdenes | Ver historial de sus propias órdenes |

## Alcance v1.0

- CRUD completo de clientes y vehículos
- Apertura de órdenes de trabajo con al menos un ítem de repuesto (composición: ítem no existe sin orden)
- Inicio y finalización de órdenes con descuento de stock en una sola transacción (Unit of Work)
- Catálogo de estados de orden: PENDIENTE, EN_REPARACION, TERMINADA, CANCELADA
- Autenticación con contraseñas hasheadas con bcrypt y token JWT en cookie `access_token` HttpOnly
- Autorización por roles vigentes en base de datos en cada petición (401 vs 403 distinguidos)
- Límite de 5 intentos fallidos de login en 60 segundos (respuesta 429)
- Registro de cliente con usuario, rol CLIENTE y ficha de cliente en una sola transacción (todo o nada)
- Historial inmutable de estados de orden, movimientos de stock y cambios de precio
- Tablas de "sólo agregado" protegidas por trigger en PostgreSQL (segunda migración de Alembic escrita a mano)
- Endpoints de salud (`/health/live`, `/health/ready`)
- Datos iniciales cargados por `seed.py` (incluido el catálogo de estados)

## Fuera de alcance

- Concurrencia y bloqueos de filas (capítulo 7 — tema de la próxima clase)
- Colas de tareas con Redis (capítulo 8); el aviso al cliente se resuelve con `BackgroundTasks` simulado en el mismo proceso
- Frontend propio (la API es backend puro; los clientes consumen vía API externa o móvil no incluida en este TP)
- Pago real integrado; el aviso al cliente es simulado

## Métricas de éxito

- Todas las 20 reglas de negocio (RN-01 a RN-20) implementadas y verificables
- Ninguna entrada inválida termina en error 500
- Esquema creado exclusivamente con `alembic upgrade head` (no `create_all`)
- Downgrade y upgrade de migraciones funcionan sobre base vacía
