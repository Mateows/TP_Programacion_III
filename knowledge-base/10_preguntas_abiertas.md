# Preguntas Abiertas

## Inconsistencias detectadas

### IN-01 — Conteo de reglas de negocio (resuelto)
**Resolución**: La consigna oficial define 20 reglas de negocio, desde RN-01 hasta RN-20. Las referencias anteriores a 18 reglas quedaron obsoletas.  
**Impacto**: Ninguno — `05_reglas_de_negocio.md` documenta las 20 reglas de forma canónica.  
**Estado**: Cerrado / obsoleto.

### IN-02 — Driver asíncrono de PostgreSQL
**Documento A dice**: asyncpg (0.30).  
**Documento B dice**: psycopg 3 asíncrono (del capítulo 4).  
**Impacto**: La cadena de conexión en `app/core/database.py` depende de esta elección.  
**Resolución propuesta**: Definir en `.env` y usar el que esté disponible en el entorno de desarrollo.

### IN-03 — Alcance del aviso al cliente
**Documento A dice**: Simulado con BackgroundTasks, se pierde si el proceso se reinicia.  
**Documento B dice**: No hay colas de Redis (capítulo 8 es futuro).  
**Impacto**: Si se requiere notificación confiable, falta infraestructura.  
**Resolución proposta**: Aceptado por el TP; documentado como riesgo.

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|-----------|----------|---------|---------|
| Alta | ¿Driver asíncrono: asyncpg o psycopg3? | Sprint 1 (configuración de DB) | Equipo técnico |
| Baja | ¿Integración externa futura (pagos, notificaciones reales)? | Lanzamiento | Product Owner |
