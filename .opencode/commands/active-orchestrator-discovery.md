---
description: "Ejecuta solo la fase de Discovery/Investigación del Active Orchestrator"
---

# Active Orchestrator — Discovery

Ejecuta la fase de Discovery/Investigación antes de armar la Knowledge Base. Investiga:

- Problema que resuelve el sistema
- Usuarios objetivo y actores
- Casos de uso principales
- Competidores (si hay URLs, se scrajean con `web-scraper`)
- Funcionalidades necesarias y opcionales
- Reglas de negocio
- Integraciones externas
- Restricciones y riesgos
- Preguntas abiertas priorizadas

El resultado se guarda en la sección `discovery` de `.active-orchestrator-state.json`.

## Uso

```
/active-orchestrator:discovery
```

Esta fase es interactiva: se hace una Q&A sobre el checklist completo antes de producir el output. No construye la KB en sí (eso lo hace `kb-creator` en el siguiente paso).