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
source .venv/bin/activate  # o anteponer `uv run` a cada comando

# Añadir una fuente de información
social-agent sources add "Rust Blog" rss "https://blog.rust-lang.org/feed" --priority 1

# Listar fuentes
social-agent sources list

# Listar seeds (ideas)
social-agent seeds list

# Listar drafts por plataforma
social-agent drafts list --platform twitter

# Aprobar y publicar un draft
social-agent drafts approve <draft_id>
social-agent drafts publish <draft_id>
```

## Personalización

Copia los ejemplos de `templates/` a `data/` y edítalos:

```bash
cp templates/prompts/interests.md data/prompts/
cp -r templates/prompts/platforms data/prompts/
```

Luego ajusta `data/prompts/interests.md` con tus temas de interés y
`data/prompts/platforms/*.md` con el tono y ejemplos para cada red.

## Estructura

```
social-agent/
├── backend/        → Python + FastAPI + CLI
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
