# Estructura del proyecto

```
social-agent/
├── backend/        → Python + FastAPI + CLI + publicadores
├── frontend/       → TypeScript + Astro (en desarrollo)
├── data/           → Persistencia en markdown (generado en runtime, ignorado por git)
│   ├── prompts/    → Intereses y prompts de plataforma
│   ├── sources/    → Fuentes de información
│   ├── seeds/      → Ideas generadas
│   ├── drafts/     → Drafts de posts
│   └── published/  → Posts publicados
├── templates/      → Ejemplos de configuración (trackeados en git)
│   └── prompts/    → interests.md, platforms/{twitter,linkedin}.md
├── tests/          → Tests unitarios
└── AGENTS.md       → Plan del proyecto y fases
```

Ver `AGENTS.md` para el detalle completo del plan y el workflow del proyecto.
