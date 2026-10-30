# Flujos Principales

Cada flujo se documenta extremo a extremo, mostrando interacciones entre componentes.

## Flujo 1: Registro de cliente (auto-registro, Unit of Work)
**Disparador**: cliente nuevo envía `POST /auth/registro`  
**Actor**: Cliente (no autenticado)

**Pasos:**
1. Router construye el Unit of Work con una dependencia y lo pasa al Service sin abrirlo
2. Service abre el Unit of Work con `async with`
3. Service valida que el documento no pertenezca a un cliente existente (RN-01, RN-02)
4. Repository crea el usuario (bcrypt fuera del bucle, hash calculado antes de abrir transacción)
5. Repository crea el rol CLIENTE en `asignacion_rol`
6. Repository crea la ficha de cliente con `usuario_id` apuntando al usuario creado
7. Unit of Work confirma al salir del bloque (todo o nada)
8. Router traduce errores a códigos HTTP (201, 409, 422)

**Diagrama de secuencia:**
```
Cliente → Router → Service → UnitOfWork → Repository → DB
                                    ← confirma (todo o nada)
Router → Cliente (201 / 409 / 422)
```

**Casos de error:**
- Documento duplicado → 409, ninguna fila suelta (RN-02)
- Cuerpo inválido → 422

---

## Flujo 2: Login con límite de intentos
**Disparador**: cliente envía `POST /auth/login`  
**Actor**: Cualquiera

**Pasos:**
1. Router lee la cookie `access_token` de `request.cookies`
2. Service consulta `intento_acceso` para contar fallos del mismo correo desde la misma IP en 60 segundos (RN-08)
3. Si se superó el límite, responde 429 con `Retry-After` sin calcular hash
4. Si no, verifica la contraseña contra el hash del usuario o contra un hash ficticio si el correo no existe (RN-09)
5. Si es correcto, emite JWT con `sub`, `iat`, `exp` y roles vigentes al emitirlo
6. Anota el intento en `intento_acceso` desde una sesión y transacción propias (se confirma siempre, aunque la petición falle)
7. Router envía el token solo en cookie `Set-Cookie` con `HttpOnly`, `SameSite=Lax`, `Max-Age`
8. Cuerpo responde sin token: `{ mensaje, debe_cambiar_password, expira_en_segundos }`

**Diagrama de secuencia:**
```
Cliente → Router → Service → Repository → DB (intento_acceso)
                                   ← verifica hash (real o ficticio)
Router → Cliente (Set-Cookie, 200 / 401 / 422 / 429)
```

**Casos de error:**
- Límite superado → 429, no verifica contraseña (RN-08)
- Contraseña mala o correo inexistente → 401, mismo cuerpo y tiempo parecido (RN-09)

---

## Flujo 3: Apertura de orden de trabajo (composición, ítem sin orden no existe)
**Disparador**: recepción envía `POST /ordenes`  
**Actor**: Recepción o Administrador

**Pasos:**
1. Router construye el Unit of Work y lo pasa al Service
2. Service abre el Unit of Work con `async with`
3. Service valida que el catálogo `estado_orden` no esté vacío (RN-19)
4. Service crea la orden con estado PENDIENTE, al menos un ítem, sin repuestos repetidos (RN-10)
5. Repository copia el precio de cada repuesto en el ítem; el servidor calcula el total (RN-10)
6. Repository crea la primera línea de historial: `desde_estado = null`, `hasta_estado = PENDIENTE` (RN-10)
7. Unit of Work confirma
8. Router responde 201 con precios copiados, total e historial

**Diagrama de secuencia:**
```
Recepción → Router → Service → UnitOfWork → Repository → DB
                                    ← confirma
Router → Recepción (201 con precios, total, historial / 409 / 422)
```

**Casos de error:**
- Catálogo vacío → 409 (RN-19)
- Repuesto inexistente → 409, orden no creada (C-10)
- Cuerpo inválido → 422

---

## Flujo 4: Terminar orden (transacción atómica, descuento de stock)
**Disparador**: mecánico asignado o administrador envía `POST /ordenes/{id}/terminar`  
**Actor**: Mecánico asignado o Administrador

**Pasos:**
1. Router construye el Unit of Work y lo pasa al Service
2. Service abre el Unit of Work con `async with`
3. Service verifica que la orden esté EN_REPARACION y que el actor sea el mecánico asignado o ADMIN (RN-11)
4. Para cada ítem de la orden:
   - Verifica que haya stock suficiente (RN-13)
   - Descuenta el stock del repuesto
   - Crea un movimiento de stock (salida)
5. Crea una línea de historial: `EN_REPARACION → TERMINADA`
6. Unit of Work confirma al salir del bloque
7. Si un repuesto no alcanza, se revierte todo: no queda ninguna escritura (RN-13)
8. Agenda aviso al cliente con `BackgroundTasks` (simulado, después de enviar la respuesta)
9. Router responde 200 o 403 / 404 / 409

**Diagrama de secuencia:**
```
Mecánico → Router → Service → UnitOfWork → Repository → DB
                                   ← confirma (todo o nada, rollback si falla stock)
Service → BackgroundTasks (aviso al cliente, después de la respuesta)
Router → Mecánico (200 / 403 / 404 / 409)
```

**Casos de error:**
- Stock insuficiente → 409, rollback completo (RN-13, C-11)
- No es el mecánico asignado ni ADMIN → 403
- Orden no existe → 404
- Estado no permite terminar → 409

---

## Flujo 5: Cambio de rol de usuario (autoprotección, historial)
**Disparador**: administrador envía `POST /usuarios/{id}/roles` o `DELETE /usuarios/{id}/roles/{rol}`  
**Actor**: Administrador

**Pasos:**
1. Router construye el Unit of Work y lo pasa al Service
2. Service abre el Unit of Work con `async with`
3. Service verifica que el administrador no se revoca su propio rol ADMIN (RN-05)
4. Service verifica que quede al menos un administrador vigente (RN-05)
5. Repository revoca (escribe `revocada_en`) o crea nueva asignación con `desde` y `vence_en`
6. Unit of Work confirma
7. Se registra en `evento_seguridad` con actor `SISTEMA` o el administrador actuante

**Diagrama de secuencia:**
```
Admin → Router → Service → UnitOfWork → Repository → DB (asignacion_rol, evento_seguridad)
                                   ← confirma
Router → Admin (200 / 201 / 404 / 409)
```

**Casos de error:**
- Autoprotección (revocarse ADMIN a sí mismo) → 409 (RN-05)
- Quedar sin administradores vigentes → 409 (RN-05)
- Vencimiento en el pasado o sin zona horaria → 422
