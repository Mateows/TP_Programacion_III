# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — API backend pura, sin frontend propio
**Decisión**: La API es backend puro; no hay frontend incluido en este TP.  
**Contexto**: El TP pide endpoints REST y el login devuelve el token en cookie, no en el cuerpo. Los clientes se registran por "la web" pero esa web no está en el alcance del entregable.  
**Alternativas consideradas**: Incluir un frontend simple (React, HTML vanilla).  
**Justificación**: El TP se centra en backend (capas, transacciones, autenticación, autorización); agregar frontend diluiría el foco y no está en los ejercicios 1-8.  
**Trade-offs aceptados**: Los clientes consumen la API desde una web externa o móvil no incluida.

### DD-02 — Stack tecnológico obligatorio del TP
**Decisión**: Usar exactamente el stack listado en los requisitos técnicos (Python 3.12, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, PostgreSQL 16, Alembic 1.13 async, bcrypt 4.0, PyJWT 2.8).  
**Contexto**: El TP especifica versiones mínimas y herramientas por capítulo.  
**Alternativas consideradas**: Stack más moderno o diferente (ej. FastAPI + MongoDB, o otro ORM).  
**Justificación**: El TP evalúa capítulos específicos; desviarse del stack rompería la alineación con los ejercicios.  
**Trade-offs aceptados**: Menos flexibilidad para elegir herramientas, pero alineación total con los criterios de evaluación.

### DD-03 — Alembic en lugar de `create_all`
**Decisión**: El esquema se crea exclusivamente con Alembic; `create_all` está prohibido.  
**Contexto**: Requisito técnico explícito del TP.  
**Alternativas consideradas**: Usar `Base.metadata.create_all` para simplicidad.  
**Justificación**: El TP evalúa migraciones, incluyendo una escrita a mano para el disparador de sólo agregado.  
**Trade-offs aceptados**: Mayor complejidad inicial, pero versión de esquema controlada y disparador de DB posible.

### DD-04 — Driver asyncpg o psycopg3 async
**Decisión**: Usar controlador asíncrono de PostgreSQL (asyncpg o psycopg 3 asíncrono, según el capítulo 4).  
**Contexto**: El TP acepta ambos.  
**Alternativas consideradas**: Elegir uno solo y descartar el otro.  
**Justificación**: Dejar la decisión abierta hasta la implementación, según lo que esté disponible en el entorno.  
**Trade-offs aceptados**: Pequeña incertidumbre hasta definir el driver en `.env` y `database.py`.

### DD-05 — Estructura estricta de 6 capas por módulo
**Decisión**: Router → Service → UoW → Repository → Models → Schemas en todos los módulos.  
**Contexto**: El TP exige esta organización por módulo funcional.  
**Alternativas consideradas**: Estructura por capa (todos los routers juntos, todos los modelos juntos, etc.).  
**Justificación**: Cada módulo es autónomo y fácil de navegar; cumple con el requisito de "cada capa sabe lo suyo y nada más".  
**Trade-offs aceptados**: Más archivos y directorios, pero mejor organización para un proyecto creciendo.

## Supuestos inferidos

### SU-01 — Aviso al cliente simulado con BackgroundTasks
**Supuesto**: El aviso al cliente se resuelve con `BackgroundTasks` dentro del mismo proceso, simulado con `await asyncio.sleep(0.5)` y un mensaje en el registro.  
**Origen**: Requisito no funcional del TP (sección 3.9).  
**Riesgo si es falso**: Si se requiere envío real de notificaciones (email, WhatsApp), hay que agregar una integración externa y posiblemente una cola de tareas.  
**Cómo validar**: Confirmar con el docente si el aviso simulado es suficiente para la entrega.

### SU-02 — 20 reglas de negocio (RN-01 a RN-20)
**Decisión**: La consigna oficial define 20 reglas de negocio, desde RN-01 hasta RN-20. Las referencias anteriores a 18 reglas quedaron obsoletas.  
**Origen**: Corrección durante la revisión documental; alineado con `05_reglas_de_negocio.md`.  
**Riesgo si es falso**: Ninguno — la consigna oficial es normativa y define 20 reglas.

### SU-03 — Escala: equipo pequeño (< 50 personas)
**Supuesto**: El sistema opera a escala de un solo taller (equipo pequeño).  
**Origen**: Respuesta P0-scale durante la fundación.  
**Riesgo si es falso**: Si el sistema debe soportar múltiples talleres o miles de usuarios, cambian las decisiones de DB y caché.  
**Cómo validar**: Confirmar si el TP contempla múltiples sucursales o solo una.

### SU-04 — Prioridad de calidad: mantenibilidad
**Supuesto**: Se prioriza mantenibilidad sobre velocidad, escalabilidad o costo.  
**Origen**: Respuesta P5 durante la fundación.  
**Riesgo si es falso**: Si se prioriza velocidad, se podría aceptar deuda técnica que este diseño evita.  
**Cómo validar**: Ninguna; es una decisión de diseño del proyecto.

### SU-05 — No hay competidores externos
**Supuesto**: Es un TP académico; no busca competir ni implementarse en ninguna empresa.  
**Origen**: Respuesta durante la fase de Discovery.  
**Riesgo si es falso**: Si el proyecto evoluciona a un producto real, faltaría análisis de competencia.  
**Cómo validar**: Reevaluar si el proyecto trasciende el ámbito académico.
