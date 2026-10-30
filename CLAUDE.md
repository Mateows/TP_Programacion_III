# Taller mecánica — Instrucciones para Agentes

API backend pura (sin frontend propio) para un taller mecánico. Gestiona clientes, vehículos, órdenes de trabajo con ítems de repuestos, control de stock, autenticación con bcrypt + JWT en cookie HttpOnly, autorización por roles vigentes en base de datos, y transacciones atómicas mediante el patrón Unit of Work. Construida con FastAPI, SQLModel/SQLAlchemy async y PostgreSQL 16, con migraciones vía Alembic y datos iniciales cargados por `seed.py`.

## Stack Tecnológico

| Capa | Tecnología | Versión mínima |
|------|------------|----------------|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI | 0.111 |
| Modelos de tabla | SQLModel | 0.0.24 |
| Motor / sesión / carga anticipada | SQLAlchemy | 2.0 (asíncrono) |
| Controlador de PostgreSQL | asyncpg o psycopg 3 asíncrono | 0.30 / capítulo 4 |
| Base de datos | PostgreSQL | 16 |
| Migraciones | Alembic | 1.13 (plantilla asíncrona) |
| Configuración | pydantic-settings | 2.0 |
| Hash de contraseñas | bcrypt | 4.0 |
| Token firmado | PyJWT | 2.8 |
| Servidor ASGI | uvicorn | el que instala `fastapi[standard]` |

## Base de Conocimiento

| Archivo | Contenido |
|---------|-----------|
| [knowledge-base/README.md](knowledge-base/README.md) | Resumen ejecutivo e índice |
| [knowledge-base/01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Propósito, objetivos por actor, alcance, fuera de alcance |
| [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack tecnológico, arquitectura general, integraciones externas |
| [knowledge-base/03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Actores del sistema, matriz RBAC, permisos, rutas públicas |
| [knowledge-base/04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, relaciones, seed data |
| [knowledge-base/05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | 20 reglas de negocio codificadas (RN-01 a RN-20) |
| [knowledge-base/06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario organizadas por épica |
| [knowledge-base/07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos extremo a extremo (auth, dominio principal, transacciones) |
| [knowledge-base/08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura de directorios, seguridad, env vars |
| [knowledge-base/09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones de diseño + supuestos inferidos |
| [knowledge-base/10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | Inconsistencias detectadas + preguntas abiertas priorizadas |

## Skills Disponibles

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| Backend Core | FastAPI / SQLModel / UoW / Repository | `fastapi-expert`, `auth-implementation-patterns` |
| Seguridad | Autenticación / Autorización | `auth-implementation-patterns` |
| Testing / Calidad | TDD / Pruebas | `tdd` |
| Orquestación | OPSX / SDD / Foundation | `skill-registry` |

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo).

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

## Reglas Duras (específicas del proyecto)

1. `snake_case` para nombres de variables, funciones, archivos.
2. Type hints obligatorios en todas las firmas.
3. Pydantic V2 sintaxis (`field_validator`, `model_validator`, `model_config`) — nunca V1 (`@validator`, `class Config`).
4. `extra="forbid"` en contratos de entrada.
5. `X | None` en lugar de `Optional[X]`.
6. `async/await` para toda I/O; ninguna llamada bloqueante.
7. bcrypt fuera del bucle de eventos (`to_thread` + semáforo).
8. JWT solo en cookie `access_token` con `HttpOnly`, `SameSite=Lax`, `Max-Age`; nunca en el cuerpo.
9. Alembic para migraciones; **prohibido** `create_all`.
10. Dinero en `NUMERIC` / `Decimal`, nunca `float`.
11. Fechas en `timestamptz`.
12. Carga anticipada en repositorios (sin N+1, sin carga perezosa).
13. Unit of Work: confirma al salir del bloque, revierte con excepción; **nunca** `commit()` en repositorio.
14. Secrets solo en entorno (`.env` no versionado); sin valores por defecto.
15. Estructura de 6 capas por módulo: Router → Service → UoW → Repository → Models → Schemas.
16. **Control de versiones:** Está prohibido ejecutar `git commit` o `git push` automáticamente. La creación de commits y la sincronización del repositorio quedan exclusivamente bajo el control manual del usuario. Estas operaciones sólo podrán realizarse después de una solicitud explícita del usuario para esa acción concreta.

## Roadmap de Changes

Ver `CHANGES.md` en la raíz. 9 changes organizados en 6 fases:

- **C-01** `foundation-setup` (BAJO)
- **C-02** `core-models` (CRITICO)
- **C-03** `auth` (CRITICO)
- **C-04** `usuarios-y-roles` (ALTO)
- **C-05** `clientes-y-vehiculos` (MEDIO)
- **C-06** `repuestos-stock` (MEDIO)
- **C-07** `ordenes-de-trabajo` (CRITICO)
- **C-08** `consulta-cliente` (BAJO)
- **C-09** `integracion-final-migraciones-validacion` (BAJO)

Camino crítico (ilustrativo): C-01 → C-02 → C-03 → C-05 → C-07 → C-09. Las ramas paralelas se ejecutan de forma concurrente: tras C-03, C-04, C-05 y C-06 pueden ejecutarse en paralelo; C-07 requiere que C-03, C-04, C-05 y C-06 estén listas; C-08 corre tras C-07; y C-09 integra una vez que C-04, C-05, C-06, C-07 y C-08 estén completas.

Primer change recomendado: `/opsx:propose C-01-foundation-setup`.

## Flujo de Trabajo

KB → CHANGES.md → `/opsx:propose <change>` → implementar → `/opsx:archive <change>`.
