# social-agent

Sistema de agentes para gestión de redes sociales.

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

El flujo de trabajo tiene tres etapas: **fuentes** → **semillas** → **drafts**.

### Fuentes (`sources`)

Registra de dónde quieres obtener información (RSS, webs, APIs sociales). Cada fuente tiene una prioridad (1 alta, 3 baja) que el *agente ideador* usará para ponderar su contenido.

```bash
social-agent sources add "Rust Blog" rss "https://blog.rust-lang.org/feed" --priority 1
social-agent sources list
```

### Semillas (`seeds`)

Las semillas son ideas generales para posts, generadas por el ideador a partir de las fuentes y tus intereses. Se listan, revisan y pueden descartarse.

```bash
# Ver todas las semillas
social-agent seeds list

# Ver solo las pendientes
social-agent seeds list --status pending

# Ver el detalle de una semilla
social-agent seeds show <seed_id>

# Descartar una semilla
social-agent seeds discard <seed_id>
```

### Drafts (`drafts`)

Los borradores son versiones concretas del post adaptadas a cada plataforma (Twitter, LinkedIn, etc.), generadas por el *agente escritor* a partir de una semilla. Se revisan, editan, aprueban y publican.

```bash
# Ver todos los borradores
social-agent drafts list

# Ver los borradores de Twitter
social-agent drafts list --platform twitter

# Ver los borradores aprobados
social-agent drafts list --status approved

# Ver el detalle de un borrador
social-agent drafts show <draft_id>

# Aprobar un borrador para su publicación
social-agent drafts approve <draft_id>

# Rechazar un borrador con una nota
social-agent drafts reject <draft_id> --notes "muy técnico"

# Editar un borrador
social-agent drafts edit <draft_id> "nuevo contenido"

# Marcar un borrador como publicado
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
