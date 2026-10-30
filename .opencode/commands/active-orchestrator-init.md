---
description: "Inicializa el flujo de fundación (foundation flow) de un proyecto nuevo usando Active Orchestrator"
---

# Active Orchestrator — Init

Ejecuta el flujo de fundación completo de un proyecto nuevo, paso a paso, siguiendo el orden definido en §4.2:

1. **`openspec init`** — Inicializa la raíz OpenSpec del proyecto
2. **Pregunta si correr Discovery** — Si el usuario acepta, despacha `discovery-research`
3. **Despacha cada fase en orden:**
   - `discovery-research` → Investigación de mercado, usuarios, casos de uso, competidores, reglas de negocio
   - `kb-creator` → Construye la Knowledge Base (10 archivos `.md` en `knowledge-base/`)
   - `design-system` → Define el sistema de diseño
   - `roadmap-generator` → Genera `CHANGES.md` con dependencias, camino crítico y plan de implementación
   - `find-skill` → Descubre e instala skills necesarias
   - `skill-registry` → Crea/actualiza `.atl/skill-registry.md`
   - `agent-instruction` → Genera `AGENTS.md` / `CLAUDE.md` del proyecto

**Estado compartido:** Todo se registra en `.active-orchestrator-state.json` (campo `step` y resultados por fase).

## Uso

```
/active-orchestrator:init
```

Cuando se invoque, yo (el agente) ejecutaré cada fase secuencialmente, preguntando antes de correr Discovery y mostrando el progreso de cada etapa. Al terminar, el proyecto tendrá su foundation completa lista para empezar a implementar cambios con `/opsx:propose`.

---

**Nota para disponibilidad global:** Si querés que este comando esté disponible en *todos* tus proyectos (no solo en este), copiá este archivo al directorio global de comandos de OpenCode (en Windows suele ser `%USERPROFILE%\.opencode\commands\` o la ruta que indique `opencode config`).