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

### Migraciones de base de datos (Alembic)

El backend SQLite usa [Alembic](https://alembic.sqlalchemy.org/) para el control
de versiones del esquema. Las migraciones viven en `backend/alembic/versions/`.

```bash
# Aplicar todas las migraciones pendientes
cd backend && alembic upgrade head

# Revertir la última migración
cd backend && alembic downgrade -1

# Generar una migración a partir de cambios en los modelos ORM (db.py)
cd backend && alembic revision --autogenerate -m "descripción del cambio"
```

> **Nota sobre la ruta de la base de datos:** `settings.data_dir` es relativa al
> CWD, por lo que `alembic` ejecutado desde `backend/` resuelve la DB a
> `backend/data/social_agent.db` en vez de `data/social_agent.db` (raíz del
> proyecto). Si tu DB con datos está en la raíz, apunta a ella explícitamente:
>
> ```bash
> cd backend && SOCIAL_AGENT_SQLITE_PATH=$(pwd)/../data/social_agent.db alembic upgrade head
> ```
>
> Alternativamente, ejecuta `alembic` desde la raíz del proyecto. Sin este
> ajuste, `upgrade head` no informará error pero actuará sobre una DB vacía y la
> migración no se aplicará a tus datos reales.

## Uso básico

El flujo de trabajo tiene cuatro etapas: **fuentes** → **semillas** → **ideas** → **drafts**.

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

### Ideas (`ideas`)

Las ideas son el paso intermedio entre las semillas y los borradores: el *agente
ideador* produce, a partir de una semilla aprobada, un `title` y un `summary`
fiel al artículo original. Sobre esa idea puedes añadir un **comentario** del
autor que se enviará al *agente escritor* **separado del resumen de la noticia**,
para aportar contexto personal o instrucciones de enfoque (p. ej. "empieza
narrando la publicación del modelo e indicando que es de pesos abiertos").

```bash
# Generar una idea a partir de una semilla aprobada
social-agent ideas generate <seed_id>

# Listar ideas
social-agent ideas list
social-agent ideas list --status pending

# Ver el detalle de una idea (incluye el comentario si lo tiene)
social-agent ideas show <idea_id>

# Fijar un comentario para el escritor
social-agent ideas comment <idea_id> "estaré probando este modelo esta semana"

# Eliminar el comentario
social-agent ideas comment <idea_id> --clear

# Descartar una idea
social-agent ideas discard <idea_id>
```

El comentario también puede editarse desde el frontend (página de edición de la
idea) o vía API con `PATCH /api/ideas/{id}` enviando `{"comment": "..."}`.

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

### Programación de publicaciones (`schedule`)

Los borradores pueden programarse para publicarse automáticamente en una
fecha futura. El scheduler comprueba periódicamente qué drafts han llegado
a su hora y los publica con las credenciales configuradas.

```bash
# Programar un borrador (formato ISO 8601, con o sin zona horaria)
social-agent schedule set <draft_id> 2026-06-20T15:30:00

# Listar borradores programados (ordenados por fecha)
social-agent schedule list

# Cancelar la programación de un borrador
social-agent schedule cancel <draft_id>

# Publicar ahora todos los drafts cuya hora ha llegado (one-shot)
social-agent schedule publish
```

#### Lanzar el "cron" (worker en segundo plano)

Para que la publicación programada funcione de forma automática, ejecuta el
worker del scheduler en un proceso aparte (en una terminal, un `tmux`/`screen`,
o como servicio systemd):

```bash
# Comprueba cada 5 minutos (por defecto) y publica los drafts vencidos
uv run social-agent schedule worker

# Intervalo personalizado (en segundos)
uv run social-agent schedule worker --interval 60
```

El worker se ejecuta en primer plano hasta que lo detienes con `Ctrl+C`.
Mientras esté activo, cualquier draft con `scheduled_at` en el pasado y
estado `draft` se publicará automáticamente en su plataforma.

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

## API REST

La API está documentada automáticamente con OpenAPI:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/sources` | Listar fuentes (filtro opcional `?source_type=rss`) |
| `POST` | `/api/sources` | Crear fuente |
| `GET` | `/api/sources/{id}` | Obtener fuente |
| `PATCH` | `/api/sources/{id}` | Actualizar fuente |
| `DELETE` | `/api/sources/{id}` | Eliminar fuente |
| `GET` | `/api/seeds` | Listar semillas (filtros opcionales: `?status=pending`, `?statuses=pending&statuses=approved`, `?q=keyword`, `&url=fragment`) |
| `GET` | `/api/seeds/{id}` | Obtener semilla |
| `POST` | `/api/seeds/generate` | Generar semillas desde fuentes |
| `PATCH` | `/api/seeds/{id}` | Actualizar semilla |
| `GET` | `/api/ideas` | Listar ideas (`?status=pending`) |
| `GET` | `/api/ideas/{id}` | Obtener idea (incluye `comment`) |
| `POST` | `/api/ideas/generate` | Generar idea desde una semilla aprobada |
| `PATCH` | `/api/ideas/{id}` | Actualizar idea (estado, título, resumen, **comentario**) |
| `DELETE` | `/api/ideas/{id}` | Eliminar idea |
| `GET` | `/api/drafts` | Listar borradores (`?platform=twitter&status=approved`) |
| `GET` | `/api/drafts/scheduled` | Listar borradores programados |
| `GET` | `/api/drafts/{id}` | Obtener borrador |
| `POST` | `/api/drafts/generate` | Generar borradores desde una semilla |
| `PATCH` | `/api/drafts/{id}` | Actualizar borrador (estado, contenido, notas) |
| `POST` | `/api/drafts/{id}/schedule` | Programar borrador (body: `{"scheduled_at": "2026-06-20T15:30:00"}`) |
| `POST` | `/api/drafts/{id}/unschedule` | Eliminar la programación de un borrador |
| `POST` | `/api/scheduler/run` | Ejecutar el scheduler (publica drafts vencidos) |
| `POST` | `/api/publish/{id}` | Publicar borrador aprobado en la red social |

### Ejemplos con curl

```bash
# Health
curl http://localhost:8000/api/health

# Crear fuente RSS
curl -X POST "http://localhost:8000/api/sources?name=Rust+Blog&source_type=rss&url=https://blog.rust-lang.org/feed"

# Listar fuentes
curl http://localhost:8000/api/sources

# Generar semillas
curl -X POST http://localhost:8000/api/seeds/generate \
  -H "Content-Type: application/json" \
  -d '{"interests": "rust, systems programming"}'

# Generar una idea desde una semilla aprobada
curl -X POST http://localhost:8000/api/ideas/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_id": "seed_123", "interests": "rust, systems programming"}'

# Añadir un comentario del autor a una idea (lo recibe el agente escritor)
curl -X PATCH http://localhost:8000/api/ideas/idea_123 \
  -H "Content-Type: application/json" \
  -d '{"comment": "estaré probando este modelo esta semana, publicaré actualizaciones"}'

# Generar drafts (requiere idea existente)
curl -X POST http://localhost:8000/api/drafts/generate \
  -H "Content-Type: application/json" \
  -d '{"idea_id": "idea_123", "platforms": ["twitter", "linkedin"]}'

# Aprobar draft
curl -X PATCH http://localhost:8000/api/drafts/draft_123 \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'

# Publicar (requiere credenciales configuradas)
curl -X POST http://localhost:8000/api/publish/draft_123

# Programar un borrador para una fecha futura
curl -X POST http://localhost:8000/api/drafts/draft_123/schedule \
  -H "Content-Type: application/json" \
  -d '{"scheduled_at": "2026-06-20T15:30:00+00:00"}'

# Ejecutar el scheduler manualmente (publica drafts vencidos)
curl -X POST http://localhost:8000/api/scheduler/run
```
