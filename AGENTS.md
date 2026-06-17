# social-agent

Sistema de agentes para gestión de redes sociales.

## Stack

- **Backend**: Python + FastAPI
- **CLI**: Click/Typer
- **Frontend**: TypeScript + Astro
- **Persistencia**: Markdown + YAML frontmatter
- **LLM**: LiteLLM (multi-proveedor: OpenAI, Anthropic, Ollama, etc.)

## Estructura del proyecto

```
social-agent/
├── backend/
│   ├── pyproject.toml
│   └── src/social_agent/
│       ├── __init__.py
│       ├── main.py               # FastAPI app
│       ├── config.py              # LLM provider, rutas, etc.
│       ├── llm.py                 # Cliente LiteLLM unificado
│       ├── models/
│       │   ├── __init__.py
│       │   ├── source.py          # Source model + SourceType/Priority
│       │   ├── seed.py            # Seed model + SeedStatus
│       │   └── draft.py           # Draft model + DraftStatus
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── ideator.py
│       │   └── writer.py
│       ├── publishers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── twitter.py
│       │   └── linkedin.py
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── rss.py
│       │   ├── scraper.py
│       │   └── social.py
│       ├── storage/
│       │   ├── __init__.py
│       │   └── markdown_store.py  # CRUD markdown + frontmatter
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router_seeds.py
│       │   ├── router_drafts.py
│       │   ├── router_sources.py
│       │   └── router_publish.py
│       └── cli/
│           ├── __init__.py
│           └── commands.py        # Click commands
├── frontend/
│   ├── package.json
│   ├── astro.config.mjs
│   └── src/
│       ├── pages/
│       │   ├── index.astro
│       │   ├── seeds.astro
│       │   └── drafts.astro
│       └── components/
├── data/
│   ├── prompts/
│   │   ├── interests.md
│   │   └── platforms/
│   │       ├── twitter.md
│   │       └── linkedin.md
│   ├── sources/
│   ├── seeds/
│   ├── drafts/
│   └── published/
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_markdown_store.py
│   ├── test_collectors.py
│   ├── test_api.py
│   ├── test_ideator.py
│   ├── test_writer.py
│   └── test_publishers.py
├── pyproject.toml
└── AGENTS.md
```

## Workflow

1. **Cada fase** incluye escribir los tests correspondientes.
2. **Antes de cerrar una fase**, ejecutar tests y verificar que todo pasa.
3. **Avisar al usuario** al completar cada fase antes de pasar a la siguiente.
4. **README.md** se mantiene actualizado con instrucciones de instalación, uso básico y estructura del proyecto.
5. **ROADMAP.md** contiene el registro de fases completadas y planificadas.
