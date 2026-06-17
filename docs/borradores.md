# Generación y publicación de borradores

## WriterAgent — prompts

La generación de borradores está a cargo de `WriterAgent` (`backend/src/social_agent/agents/writer.py`).

### SYSTEM_PROMPT (línea 10)

```
Eres un writer de contenido para redes sociales.

Tu trabajo es transformar ideas (seeds) en posts listos para publicar en una plataforma específica.

Reglas:
- Responde SOLO con el contenido del post, sin explicaciones ni markdown adicional.
- Sigue al pie de la letra las instrucciones de tono y estilo de la plataforma.
- No añadas hashtags a menos que la plataforma los requiera explícitamente.
- Encierra el post final entre las etiquetas <post> y </post>.
  Todo lo que esté fuera de esas etiquetas será ignorado.
```

### Mensaje de usuario (línea 65)

Se construye combinando la semilla con las instrucciones de la plataforma:

```
## Idea / Seed

Título: {seed.title}
Resumen: {seed.summary}
Tags: {tags}

## Instrucciones de plataforma

{platform_instructions}

## Tarea

Genera un post para {platform_name} basado en la idea anterior.
Respeta el límite de caracteres.
Envuelve el post final entre <post> y </post>.
```

- `{platform_instructions}` se reemplaza con el cuerpo del archivo de la plataforma (sin frontmatter).
- `{platform_name}` se obtiene del campo `title` en el frontmatter del mismo archivo.

---

## Prompts de plataforma

Cada plataforma tiene un archivo markdown en `data/prompts/platforms/` con frontmatter YAML y cuerpo markdown:

```markdown
---
title: Twitter / X
lang: es
max_chars: 280
---

Tono: Directo, técnico pero accesible, con gancho...
```

| Archivo           | Plataforma |
|-------------------|------------|
| `twitter.md`      | Twitter/X  |
| `linkedin.md`     | LinkedIn   |

### Frontmatter

| Campo       | Descripción                              |
|-------------|------------------------------------------|
| `title`     | Nombre legible de la plataforma          |
| `lang`      | Idioma del contenido                     |
| `max_chars` | Límite de caracteres (0 = sin límite)    |

### Cuerpo

Contiene instrucciones de tono, estilo, ejemplos aceptables y no aceptables. Solo el cuerpo se pasa al LLM.

---

## Algoritmo de generación

### 1. Seleccionar semilla

Se carga la semilla desde `data/seeds/{seed_id}.md`. Debe tener `status = pending`. Si ya está en otro estado (`used`, `discarded`), se rechaza la operación.

### 2. Cargar instrucciones de plataforma

Se lista `data/prompts/platforms/*.md`. Por cada plataforma solicitada se abre el archivo y se extrae:
- `frontmatter['title']` → nombre legible
- `frontmatter['max_chars']` → límite de caracteres
- `post.content.strip()` → instrucciones de tono/estilo

### 3. Construir prompt

Se interpola la información de la semilla (título, resumen, tags) y las instrucciones de la plataforma en el mensaje de usuario.

### 4. Invocar LLM

`WriterAgent.generate_draft()` llama a `BaseAgent.run()` que envía dos mensajes a LiteLLM:

- **system**: `SYSTEM_PROMPT` del WriterAgent
- **user**: prompt formateado con semilla + plataforma

LiteLLM reenvía al proveedor configurado (`settings.llm_provider`). Se usa `temperature=0.7` y `max_tokens=4096`.

### 5. Parsear respuesta

`_extract_post()` intenta extraer el contenido del post en dos pasos:

1. Busca el bloque delimitado por `<post>` y `</post>` con expresión regular.
2. Si no encuentra etiquetas, elimina líneas de "thinking" (las que empiezan por `we need to`, `let me`, `i'll`, `i will`, etc. o contienen `seed idea`) y devuelve el resto.

### 6. Aplicar límite de caracteres

Si `max_chars > 0` y el contenido extraído excede ese límite, se trunca en el último espacio antes del límite (`rsplit(" ", 1)[0]`).

### 7. Crear y persistir Draft

```python
Draft(
    seed_id=seed.id,
    platform=platform,
    content=content,
    status=DraftStatus.draft,
)
```

Si no es `dry_run`, se guarda con `MarkdownStore[Draft].save()` y la semilla se marca como `SeedStatus.used`.

---

## Ciclo de vida del borrador

```
     ┌──────────┐
     │  draft   │ ◄──── crear, editar
     └────┬─────┘
          │ approve / PATCH
          ▼
     ┌──────────┐
     │ approved │
     └────┬─────┘
          │ publish
          ▼
     ┌───────────┐     ┌──────────┐
     │ published │     │  failed  │
     └───────────┘     └──────────┘

     ┌──────────┐
     │ rejected │
     └──────────┘
```

| Transición               | Cómo                          |
|--------------------------|-------------------------------|
| `draft` → `approved`     | CLI `drafts approve <id>` o API `PATCH /drafts/{id}` con `status: approved` |
| `draft` → `rejected`     | CLI `drafts reject <id>` o API `PATCH /drafts/{id}` con `status: rejected` |
| `approved` → `published` | CLI `drafts publish <id>` o API `POST /publish/{id}` |
| `approved` → `failed`    | Automático si falla la publicación |
| Cualquiera → `draft`     | Editar contenido (CLI `drafts edit` o API `PATCH` con `content`) |

Solo los borradores en estado `approved` pueden publicarse.

---

## Publicación

### Twitter (`backend/src/social_agent/publishers/twitter.py`)

Usa **Tweepy** (API v2). Requiere credenciales OAuth 1.0a (`consumer_key`, `consumer_secret`, `access_token`, `access_token_secret`). Llama a `client.create_tweet(text=draft.content)`.

### LinkedIn (`backend/src/social_agent/publishers/linkedin.py`)

Usa **httpx** contra la REST API de LinkedIn. Requiere `access_token` (OAuth 2.0) y opcionalmente `author_urn`. Si no se proporciona `author_urn`, lo resuelve automáticamente desde `/rest/userinfo`.

### Flujo de publicación

1. Validar que el borrador esté `approved`.
2. Incrementar `publish_attempts` en 1.
3. Invocar al publisher correspondiente según `draft.platform`.
4. Si la publicación es exitosa: `status = published`, `platform_post_id = resultado`, `published_at = ahora`, `publish_error = None`.
5. Si falla: `status = failed`, `publish_error = mensaje de error`.

---

## Modelo Draft y representación en disco

### Draft (Pydantic) — `backend/src/social_agent/models/draft.py`

| Campo              | Tipo                  | Default                    |
|--------------------|-----------------------|----------------------------|
| `id`               | `str`                 | `draft_{timestamp}`        |
| `seed_id`          | `str`                 | —                          |
| `platform`         | `str`                 | —                          |
| `content`          | `str`                 | `""`                       |
| `status`           | `DraftStatus`         | `draft`                    |
| `notes`            | `str \| None`         | `None`                     |
| `platform_post_id` | `str \| None`         | `None`                     |
| `publish_error`    | `str \| None`         | `None`                     |
| `publish_attempts` | `int`                 | `0`                        |
| `created_at`       | `datetime`            | `now(UTC)`                 |
| `published_at`     | `datetime \| None`    | `None`                     |

`DraftStatus` enum: `draft`, `approved`, `rejected`, `published`, `failed`.

### En disco

Cada borrador se serializa como archivo markdown con YAML frontmatter:

```markdown
---
id: draft_1718563200.000000
seed_id: seed_1718563100.000000
platform: twitter
status: draft
notes: null
platform_post_id: null
publish_error: null
publish_attempts: 0
created_at: 2025-06-17T12:00:00+00:00
---
```

Cuando se publica exitosamente:

```markdown
---
id: draft_1718563200.000000
seed_id: seed_1718563100.000000
platform: twitter
status: published
notes: null
platform_post_id: "1876543210987654321"
publish_error: null
publish_attempts: 1
created_at: 2025-06-17T12:00:00+00:00
published_at: 2025-06-17T13:00:00+00:00
---
```

`to_frontmatter()` serializa los campos omitiendo `published_at` si es `None`. `from_frontmatter()` reconstruye el modelo reconvirtiendo `status` a `DraftStatus` y las fechas a `datetime`.

---

## API REST

### Borradores (`backend/src/social_agent/api/router_drafts.py`)

| Método  | Ruta                  | Descripción                          |
|---------|-----------------------|--------------------------------------|
| `GET`   | `/drafts`             | Listar borradores (filtro por `platform` y `status`) |
| `GET`   | `/drafts/{id}`        | Obtener un borrador                  |
| `POST`  | `/drafts/generate`    | Generar borradores desde una semilla |
| `PATCH` | `/drafts/{id}`        | Actualizar estado / contenido        |

### Publicación (`backend/src/social_agent/api/router_publish.py`)

| Método  | Ruta                  | Descripción                          |
|---------|-----------------------|--------------------------------------|
| `POST`  | `/publish/{id}`       | Publicar un borrador aprobado        |

---

## CLI

| Comando                        | Descripción                              |
|--------------------------------|------------------------------------------|
| `social-agent drafts generate <seed_id>` | Generar borradores desde una semilla |
| `social-agent drafts list`     | Listar borradores                        |
| `social-agent drafts show <id>`| Mostrar un borrador                      |
| `social-agent drafts approve <id>` | Aprobar un borrador                  |
| `social-agent drafts reject <id>` | Rechazar un borrador                  |
| `social-agent drafts edit <id> <content>` | Editar contenido de un borrador |
| `social-agent drafts publish <id>` | Publicar un borrador aprobado        |
