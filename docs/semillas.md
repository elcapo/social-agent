# Generación de semillas

## Prompts del IdeatorAgent

La generación de semillas está a cargo de `IdeatorAgent` (`backend/src/social_agent/agents/ideator.py`). Usa dos prompts:

### SYSTEM_PROMPT (línea 46)

```
Eres un ideator de contenido para redes sociales.

Tu trabajo es generar ideas para posts a partir de:
1. Una lista de intereses del usuario
2. Contenido recolectado de sus fuentes de información

Reglas:
- Cada idea debe estar directamente conectada al contenido proporcionado.
- Las ideas deben ser relevantes a los intereses del usuario.
- Genera ideas variadas, no repitas el mismo ángulo.
- Responde SOLO con una lista de objetos JSON, sin markdown ni explicaciones.
- Cada objeto debe tener: title, summary, tags (lista de strings), source_index (int).
- source_index es el índice del contenido del que deriva la idea (el que está entre corchetes).
```

### USER_TEMPLATE (línea 61)

```
## Intereses del usuario

{interests}

## Contenido recolectado

{collected}

Genera entre 3 y 5 ideas para posts basadas en el contenido anterior.
```

- `{interests}` se reemplaza con el texto del archivo `data/prompts/interests.md` (solo el cuerpo, sin frontmatter YAML).
- `{collected}` se reemplaza con los ítems recolectados, formateados como:

```
--- [1] Título del artículo (nombre de la fuente) ---
URL: https://...
<primeros 500 caracteres del contenido>
```

Cada ítem lleva un índice numérico (empezando en 1) que el LLM debe usar en `source_index` para indicar de qué fuente derivó cada idea.

### interests.md

Archivo en `data/prompts/interests.md` con frontmatter YAML y cuerpo markdown:

```markdown
---
title: Soberanía, ética y pedagogía digital
priority: 1
---

1. soberanía digital (software libre, modelos de pesos abiertos, etc)
2. ética digital (tecnologías aplicadas a causas sociales, privacidad, etc)
3. pedagogía digital (lecciones de programación y otros fundamentos)
```

Solo el cuerpo del markdown se pasa al prompt. El frontmatter (`title`, `priority`) se ignora en la generación.

---

## Algoritmo de generación

La secuencia completa desde fuentes hasta semillas persistiadas:

### 1. Cargar intereses

Se lee `data/prompts/interests.md` con la librería `python-frontmatter`. Se extrae `post.content.strip()` — el cuerpo del markdown sin el frontmatter YAML.

### 2. Cargar fuentes

Se listan todas las fuentes habilitadas desde `data/sources/` usando `MarkdownStore[Source].list(filter_fn=lambda s: s.enabled)`. Opcionalmente se filtran por ID si se especifican.

### 3. Recolectar contenido

Por cada fuente, se construye el collector adecuado según su `SourceType`:

| SourceType   | Collector              |
|-------------|------------------------|
| `rss`       | `RSSCollector`         |
| `webpage`   | `WebScraperCollector`  |
| `social`    | `TwitterCollector` o `LinkedInCollector` (según la URL) |

Cada collector implementa `fetch() -> list[CollectedItem]`. Un `CollectedItem` tiene:

| Campo         | Tipo        | Descripción                        |
|---------------|-------------|------------------------------------|
| `title`       | `str`       | Título del contenido               |
| `content`     | `str`       | Texto extraído                     |
| `url`         | `str`       | URL original                       |
| `source_id`   | `str`       | ID de la fuente en el sistema      |
| `source_name` | `str`       | Nombre legible de la fuente        |
| `published`   | `datetime?` | Fecha de publicación (si aplica)   |
| `tags`        | `list[str]` | Tags asociados desde la fuente     |

Los ítems de todas las fuentes se concatenan en una sola lista.

#### Límites de contenido

Para evitar saturar el contexto del LLM, se aplican dos límites:

| Dónde | Límite | Criterio |
|---|---|---|
| `RSSCollector.MAX_ITEMS` | 20 ítems por fuente RSS | Se ordenan por `published` descendente y se toman los más recientes |
| `IdeatorAgent.MAX_TOTAL_ITEMS` | 50 ítems en total | Se ordenan por `published` descendente (cruzando todas las fuentes) y se toman los más recientes |

`TwitterCollector` y `LinkedInCollector` ya limitan a 10 resultados cada uno vía API. `WebScraperCollector` devuelve una sola página.

### 4. Construir prompt

Los ítems se formatean con índice numérico, título, nombre de fuente, URL y contenido truncado a 500 caracteres:

```python
f"--- [{idx}] {item.title} ({item.source_name}) ---\n"
f"URL: {item.url}\n"
f"{item.content[:500]}"
```

Todo se interpola en `USER_TEMPLATE` junto con el texto de intereses.

### 5. Invocar LLM

`BaseAgent.run()` envía dos mensajes a LiteLLM:

- **system**: `SYSTEM_PROMPT` del IdeatorAgent
- **user**: `USER_TEMPLATE` formateado

LiteLLM reenvía al proveedor configurado (`settings.llm_provider`): OpenAI, Anthropic, Ollama, etc. Se usa `temperature=0.7` y `max_tokens=4096`.

### 6. Parsear respuesta

`_extract_json()` intenta extraer JSON de la respuesta del LLM en tres formatos:

1. JSON directo (`json.loads`)
2. JSON dentro de bloques ```json ... ```
3. Array literal `[{...}]` embebido en el texto

Si no encuentra JSON válido, retorna lista vacía y no se generan semillas.

### 7. Mapear a Seed

Cada objeto JSON se convierte en un `Seed`:

| Campo JSON      | Campo Seed           |
|-----------------|----------------------|
| `title`         | `title`              |
| `summary`       | `summary`            |
| `tags`          | `tags`               |
| `source_index`  | se resuelve a `source_id` y `source_url` del `CollectedItem` correspondiente |

El `status` se fija a `pending` y `created_at` al momento actual.

### 8. Deduplicar

Si `force=False` (valor por defecto), se cargan todas las semillas existentes con estado `pending` y se extraen sus `source_url`. Cualquier semilla nueva cuyo `source_url` ya exista en ese conjunto se salta sin persistir.

### 9. Persistir

Cada seed se guarda con `MarkdownStore[Seed].save()` como archivo `data/seeds/{id}.md`.

---

## Modelo Seed y representación en disco

### Seed (Pydantic)

`backend/src/social_agent/models/seed.py`:

| Campo        | Tipo           | Default                  |
|--------------|----------------|--------------------------|
| `id`         | `str`          | `seed_{timestamp}`       |
| `title`      | `str`          | —                        |
| `summary`    | `str`          | —                        |
| `source_id`  | `str \| None`  | `None`                   |
| `source_url` | `str \| None`  | `None`                   |
| `tags`       | `list[str]`    | `[]`                     |
| `status`     | `SeedStatus`   | `pending`                |
| `created_at` | `datetime`     | `now(UTC)`               |

`SeedStatus` enum: `pending`, `used`, `discarded`.

### En disco

Cada seed se serializa como archivo markdown con YAML frontmatter:

```markdown
---
id: seed_1718563200.000000
title: Soberanía digital en la educación
summary: Ideas para integrar software libre en el aula...
source_id: src_001
source_url: https://ejemplo.com/articulo
tags:
  - soberanía digital
  - educación
status: pending
created_at: 2025-06-17T12:00:00+00:00
---
```

`MarkdownStore` usa dos métodos en `Seed`:

- **`to_frontmatter()`** — serializa los campos a `dict` plano (convierte `Enum` a string, `datetime` a ISO).
- **`from_frontmatter()`** — reconstruye el modelo desde el `dict` del frontmatter (reconvierte `status` a `SeedStatus`, `created_at` a `datetime`).

El cuerpo del markdown se deja vacío (`summary` viaja en frontmatter, no en el cuerpo).
