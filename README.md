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

## Configuración

Copia el fichero de entorno y edítalo:

```bash
cp .env.example .env
```

### Proveedor LLM

El sistema usa [LiteLLM](https://litellm.vercel.app/) y soporta cualquier
proveedor compatible (OpenAI, Anthropic, Ollama, etc.).

El acceso a los modelos se hace a través de **OpenCode Zen**, que expone
un endpoint compatible con la API de OpenAI:

```env
# OpenCode Zen (DeepSeek V4 Flash Free — sin coste)
SOCIAL_AGENT_LLM_PROVIDER=openai/deepseek-v4-flash-free
SOCIAL_AGENT_LLM_API_KEY=sk-...   # Tu API key de https://opencode.ai/auth
SOCIAL_AGENT_LLM_BASE_URL=https://opencode.ai/zen/v1
```

Otros modelos disponibles vía Zen (`https://opencode.ai/docs/zen/`):

```env
# SOCIAL_AGENT_LLM_PROVIDER=openai/deepseek-v4-flash
# SOCIAL_AGENT_LLM_PROVIDER=openai/gpt-5.4-nano
# SOCIAL_AGENT_LLM_PROVIDER=openai/claude-sonnet-4-6
```

También puedes usar cualquier otro proveedor directamente:

```env
# OpenAI directo
# SOCIAL_AGENT_LLM_PROVIDER=openai/gpt-4o
# SOCIAL_AGENT_LLM_API_KEY=sk-...

# Anthropic Claude
# SOCIAL_AGENT_LLM_PROVIDER=claude-3-haiku-20240307
# SOCIAL_AGENT_LLM_API_KEY=sk-ant-...

# Ollama (local)
# SOCIAL_AGENT_LLM_PROVIDER=ollama/llama3
# SOCIAL_AGENT_LLM_BASE_URL=http://localhost:11434
```

### APIs de redes sociales

Los colectores y publicadores requieren credenciales de la API correspondiente.

#### Twitter / X (API v2)

1. Ve a [developer.twitter.com](https://developer.twitter.com) y crea un proyecto.
2. Para el **colector** (lectura): genera un *Bearer Token* en "Keys and Tokens".
3. Para el **publicador** (escritura): genera credenciales OAuth 1.0a User Context
   con permisos de escritura en "Keys and Tokens" → "Access Token and Secret".
4. Añádelas al `.env`:

```env
# Colector (lectura)
SOCIAL_AGENT_TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAA...

# Publicador (escritura)
SOCIAL_AGENT_TWITTER_API_KEY=xxxxxxxxx
SOCIAL_AGENT_TWITTER_API_SECRET=xxxxxxxxx
SOCIAL_AGENT_TWITTER_ACCESS_TOKEN=xxxxxxxxx
SOCIAL_AGENT_TWITTER_ACCESS_TOKEN_SECRET=xxxxxxxxx
```

#### LinkedIn

1. Ve a [developer.linkedin.com](https://developer.linkedin.com) y crea una app.
2. Configura el redirect URI como `http://localhost:8080/callback`.
3. Añade el Client ID y Client Secret al `.env`:

```env
SOCIAL_AGENT_LINKEDIN_CLIENT_ID=xxxxxxxxx
SOCIAL_AGENT_LINKEDIN_CLIENT_SECRET=xxxxxxxxx
```

4. Genera el token de acceso automáticamente:

```bash
social-agent linkedin auth --save
```

Esto abrirá el navegador para autorizar la app y guardará el token en `.env`.
Scopes solicitados: `openid`, `profile`, `w_member_social`.

Opcionalmente puedes predefinir el author URN (se resuelve automáticamente si se omite):

```env
SOCIAL_AGENT_LINKEDIN_AUTHOR_URN=urn:li:person:xxx
```

Sin estas credenciales los colectores sociales devuelven lista vacía y los
publicadores informan del error. Las fuentes RSS y web scraping no requieren
autenticación.

## Servidores

```bash
# API REST (FastAPI) — http://localhost:8000
uv run uvicorn social_agent.main:app --reload

# Frontend (Astro) — http://localhost:4321
cd frontend && npm run dev
```

El frontend está configurado para conectar con la API en `localhost:8000`.

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

Las semillas son ideas generales para posts, generadas por el *agente ideador*
a partir de las fuentes y tus intereses. Se generan, listan, revisan y pueden
descartarse.

```bash
# Generar semillas desde las fuentes configuradas y el prompt de intereses
social-agent seeds generate

# Generar usando un fichero de intereses alternativo
social-agent seeds generate --interests data/prompts/mis-intereses.md

# Ver la respuesta cruda del LLM sin guardar (útil para depuración)
social-agent seeds generate --dry-run

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

# Publicar en la red social real (requiere credenciales configuradas)
social-agent drafts publish <draft_id>
```

Los borradores pueden tener estos estados:
`draft` → `approved` → `published` (éxito) / `failed` (error de API).
Usa `show` para inspeccionar `publish_error` en borradores fallidos:

```bash
social-agent drafts show <draft_id>
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
