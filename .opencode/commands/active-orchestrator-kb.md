---
description: "Construye la Knowledge Base (10 archivos .md) usando kb-creator"
---

# Active Orchestrator — KB Creator

Construye una Knowledge Base estructurada de 10 archivos `.md` en `knowledge-base/`:

| Archivo | Contenido |
|---------|-----------|
| `01_vision_y_objetivos.md` | Propósito, objetivos por actor, alcance, fuera de alcance |
| `02_descripcion_general.md` | Stack tecnológico, arquitectura, integraciones |
| `03_actores_y_roles.md` | Actores, matriz RBAC, permisos, rutas públicas |
| `04_modelo_de_datos.md` | Entidades, ERD, relaciones, seed data |
| `05_reglas_de_negocio.md` | Reglas de negocio codificadas |
| `06_funcionalidades.md` | Historias de usuario por épica |
| `07_flujos_principales.md` | Flujos extremo a extremo |
| `08_arquitectura_propuesta.md` | Patrones, estructura de directorios, seguridad, env vars |
| `09_decisiones_y_supuestos.md` | Decisiones de diseño + supuestos |
| `10_preguntas_abiertas.md` | Inconsistencias detectadas + preguntas priorizadas |

Tiene doble modo: silencioso (desde documentos existentes en `docs/`) o interactivo (desde cero).

## Uso

```
/active-orchestrator:kb
```