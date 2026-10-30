# Taller mecánica — Base de Conocimiento

Base de conocimiento generada a partir del TP de Programación III (Tecnicatura Universitaria en Programación) y de la etapa de Discovery previa.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos por actor, alcance, fuera de alcance |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack tecnológico, arquitectura general, integraciones externas |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores del sistema, matriz RBAC, permisos, rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Entidades, ERD, relaciones, seed data |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | 20 reglas de negocio codificadas por dominio (RN-01 a RN-20) |
| [06_funcionalidades.md](06_funcionalidades.md) | Historias de usuario organizadas por épica |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos extremo a extremo (auth, dominio principal, transacciones) |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, estructura de directorios, seguridad, env vars |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones de diseño documentadas + supuestos inferidos |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias detectadas + preguntas abiertas priorizadas |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

API backend pura (sin frontend propio) para un taller mecánico. Gestiona clientes, vehículos, órdenes de trabajo con ítems de repuestos, control de stock, autenticación con bcrypt + JWT en cookie HttpOnly, autorización por roles vigentes en base de datos, y transacciones atómicas mediante el patrón Unit of Work. Construida con FastAPI, SQLModel/SQLAlchemy async y PostgreSQL 16, con migraciones vía Alembic y datos iniciales cargados por `seed.py`.
