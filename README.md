# social-agent

Sistema de agentes para gestión de redes sociales basado en LLM.

## Requisitos

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)

## Instalación

```bash
# Clonar el repositorio
git clone <repo> && cd social-agent

# Sincronizar dependencias
uv sync

# Verificar que funciona
uv run social-agent --help
```

## Desarrollo

```bash
# Ejecutar tests
uv run pytest tests/ -v

# Linter
uv run ruff check backend/src/ tests/

# (Opcional) Activar el entorno virtual para comandos más rápidos
source .venv/bin/activate
```

## Uso básico

```bash
# Añadir una fuente de información
uv run social-agent sources add "Rust Blog" rss "https://blog.rust-lang.org/feed" --priority 1

# Listar fuentes
uv run social-agent sources list

# Listar seeds (ideas)
uv run social-agent seeds list

# Listar drafts por plataforma
uv run social-agent drafts list --platform twitter

# Aprobar y publicar un draft
uv run social-agent drafts approve <draft_id>
uv run social-agent drafts publish <draft_id>
```

## Estructura

```
social-agent/
├── backend/        → Python + FastAPI + CLI
├── frontend/       → TypeScript + Astro (en desarrollo)
├── data/           → Persistencia en markdown
│   ├── prompts/    → Intereses y prompts de plataforma
│   ├── sources/    → Fuentes de información
│   ├── seeds/      → Ideas generadas
│   ├── drafts/     → Drafts de posts
│   └── published/  → Posts publicados
├── tests/          → Tests unitarios
└── AGENTS.md       → Plan del proyecto y fases
```

Ver `AGENTS.md` para el detalle completo del plan y el workflow del proyecto.
