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
│   └── test_markdown_store.py
├── pyproject.toml
└── AGENTS.md
```

## Fases

### Fase 1 — Base del proyecto
- [x] AGENTS.md
- [x] pyproject.toml + estructura de directorios
- [x] Modelos Pydantic (Source, Seed, Draft)
- [x] MarkdownStore (CRUD con frontmatter)
- [x] CLI base con Click (skeleton de comandos)
- [x] Tests unitarios (almacenamiento y modelos) — 19 tests, todos pasan
- [x] Verificar que tests pasan

### Fase 2 — Sistema de recolección e ideación
- [x] Sistema de prompts (interests + fuentes)
- [x] Collectors (RSS, web scraping, social) — RSSCollector, WebScraperCollector, TwitterCollector, LinkedInCollector
- [x] Ideator agent (LLM vía LiteLLM)
- [x] Tests — 27 tests, todos pasan

### Fase 3 — Writer y drafts multi-plataforma
- [x] Prompts de plataforma (Twitter, LinkedIn)
- [x] Writer agent (genera drafts)
- [x] Ciclo completo vía CLI
- [x] Tests — 34 tests, todos pasan

### Fase 4 — API REST
- [x] FastAPI con routers (sources, seeds, drafts, publish)
- [x] Tests de integración — 61 tests, todos pasan

### Fase 5 — Frontend Astro
- [ ] Páginas básicas (dashboard, seeds, drafts)
- [ ] Componentes

### Fase 6 — Publicadores y APIs sociales
- [ ] Twitter publisher (API v2)
- [ ] LinkedIn publisher (API)
- [ ] Social collectors

### Fase 7 — Extensibilidad, pulido, docs
- [ ] Documentación de API
- [ ] Guía para añadir plataformas
- [ ] Tests finales

## Workflow

1. **Cada fase** incluye escribir los tests correspondientes.
2. **Antes de cerrar una fase**, ejecutar tests y verificar que todo pasa.
3. **Avisar al usuario** al completar cada fase antes de pasar a la siguiente.
4. **README.md** se mantiene actualizado con instrucciones de instalación, uso básico y estructura del proyecto.
