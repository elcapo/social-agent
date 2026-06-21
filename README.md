# social-agent

Sistema de agentes para gestión de redes sociales.

## Stack

- **Backend**: Python + FastAPI
- **CLI**: Click/Typer
- **Frontend**: TypeScript + Astro
- **Persistencia**: Markdown + YAML frontmatter
- **LLM**: LiteLLM (multi-proveedor: OpenAI, Anthropic, Ollama, etc.)

## Requisitos

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes de Python)
- Node.js >= 20.3.0
- [pnpm](https://pnpm.io/) >= 9 (gestor de paquetes del frontend)

## Instalación

```bash
# Clonar el repositorio
git clone <repo> && cd social-agent

# Sincronizar dependencias (Python)
uv sync

# Sincronizar dependencias (frontend)
cd frontend && pnpm install && cd ..

# Verificar que funciona
uv run social-agent --help
```

## Configuración

Copia el fichero de entorno y edítalo:

```bash
cp .env.example .env
```

Para configurar el proveedor LLM y las credenciales de redes sociales, consulta
la sección [Documentación](#documentación) → *Configuración*.

## Servidores

```bash
# API REST (FastAPI) — http://localhost:8000
uv run uvicorn social_agent.main:app --reload

# Frontend (Astro) — http://localhost:4321
cd frontend && pnpm dev
```

El frontend está configurado para conectar con la API en `localhost:8000`.

## Documentación

### Configuración

- [Configuración del proveedor LLM](docs/configuracion-llm.md)
- [Credenciales de Twitter / X](docs/credenciales-twitter.md)
- [Credenciales de LinkedIn](docs/credenciales-linkedin.md)
- [Desarrollo (tests, linter, migraciones)](docs/desarrollo.md)

### Uso (CLI)

El flujo de trabajo tiene cuatro etapas: **fuentes** → **semillas** → **ideas** → **borradores**.

- [Fuentes (`sources`)](docs/fuentes.md)
- [Semillas (`seeds`)](docs/semillas.md)
- [Ideas (`ideas`)](docs/ideas.md)
- [Borradores (`drafts`)](docs/borradores.md)
- [Publicación programada (`schedule`)](docs/publicacion-programada.md)

### Referencia técnica

- [Agente Ideador](docs/agente-ideador.md)
- [Agente Escritor](docs/agente-escritor.md)
- [Modelos de datos](docs/modelos-datos.md)
- [Prompts de plataforma](docs/prompts-plataforma.md)
- [API REST](docs/api-rest.md)
- [Estructura del proyecto](docs/estructura-proyecto.md)

### Guías avanzadas

- [Personalización de prompts](docs/personalizacion-prompts.md)
- [Añadir una nueva plataforma](docs/anadir-plataforma.md)
