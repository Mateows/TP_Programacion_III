---
description: "Genera las reglas del proyecto (AGENTS.md / CLAUDE.md)"
---

# Active Orchestrator — Rules

Genera el `AGENTS.md` / `CLAUDE.md` canónico del proyecto a partir de la Knowledge Base y el roadmap. Incluye:

- Stack tecnológico
- Referencia a `knowledge-base/`
- Skills disponibles por agente
- Roadmap de cambios (`CHANGES.md`)
- Reglas duras del proyecto (stack-aware, derivadas del stack real)

Es interactivo solo para confirmar las reglas duras; el resto es determinístico. No repite instrucciones del CLAUDE.md global — emite solo lo específico del proyecto.

## Uso

```
/active-orchestrator:rules
```