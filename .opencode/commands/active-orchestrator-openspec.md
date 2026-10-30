---
description: "Ejecuta la fase OpenSpec (roadmap, specs, cambios)"
---

# Active Orchestrator — OpenSpec

Ejecuta la fase OpenSpec del flujo de fundación. Genera el roadmap de cambios (`CHANGES.md`) con:

- Árbol de dependencias entre changes
- Paralelismo por fase (gates de sincronización)
- Camino crítico
- Plan óptimo con múltiples agentes
- Per-change: scope, gobernanza, dependencias, "Leer antes"

Esto prepara el proyecto para usar `/opsx:propose <change>`, `/opsx:apply`, `/opsx:archive`.

## Uso

```
/active-orchestrator:openspec
```