# Modelos de datos

Los modelos se definen con Pydantic y se persisten como archivos markdown con
YAML frontmatter mediante `MarkdownStore`
(`backend/src/social_agent/storage/markdown_store.py`).

## Source — `backend/src/social_agent/models/source.py`

| Campo           | Tipo              | Default                  |
|-----------------|-------------------|--------------------------|
| `id`            | `str`             | `src_{timestamp}`        |
| `name`          | `str`             | —                        |
| `source_type`   | `SourceType`      | —                        |
| `url`           | `str`             | —                        |
| `priority`      | `SourcePriority`  | `medium`                 |
| `tags`          | `list[str]`       | `[]`                     |
| `config`        | `dict`            | `{}`                     |
| `enabled`       | `bool`            | `True`                   |
| `created_at`    | `datetime`        | `now(UTC)`               |
| `last_fetched`  | `datetime \| None`| `None`                   |

`SourceType` enum: `rss`, `webpage`, `social`, `link_scraper`, `manual`.
`SourcePriority` enum: `high=1`, `medium=2`, `low=3`.

### En disco

```markdown
---
id: src_1718563200.000000
name: Rust Blog
source_type: rss
url: https://blog.rust-lang.org/feed
priority: 1
tags:
  - rust
  - systems
config: {}
enabled: true
created_at: 2025-06-17T12:00:00+00:00
last_fetched: null
---
```

## Seed — `backend/src/social_agent/models/seed.py`

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

El cuerpo del markdown se deja vacío (`summary` viaja en frontmatter, no en el
cuerpo).

## Draft — `backend/src/social_agent/models/draft.py`

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

## MarkdownStore

`MarkdownStore` usa dos métodos en cada modelo:

- **`to_frontmatter()`** — serializa los campos a `dict` plano (convierte `Enum`
  a string, `datetime` a ISO, omite campos `None` opcionales como
  `published_at`).
- **`from_frontmatter()`** — reconstruye el modelo desde el `dict` del
  frontmatter (reconvierte `status`/`source_type`/`priority` a su `Enum`,
  `created_at`/`published_at`/`last_fetched` a `datetime`).
