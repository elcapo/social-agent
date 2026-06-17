# Añadir una nueva plataforma

Esta guía explica cómo añadir soporte para una nueva red social (o
plataforma de publicación) en social-agent.

## Vista general

Cada plataforma necesita tres componentes:

1. **Collector** — Obtener contenido de la plataforma (fuente de ideas)
2. **Publisher** — Publicar contenido en la plataforma (opcional)
3. **Prompt** — Instrucciones para el Writer Agent (tono, estilo, límites)

## 1. Crear el prompt de plataforma

Crea un archivo en `data/prompts/platforms/<plataforma>.md` con
frontmatter YAML:

```markdown
---
title: "Mi Plataforma"
max_chars: 500
---

Escribe el post en un tono profesional y directo, como un anuncio
de producto. Usa emojis con moderación. Incluye un call-to-action
al final.

Ejemplo de tono deseado:

  "Presentamos nuestra nueva API versión 2.0 — más rápida, más
   flexible y completamente backward-compatible."

Evita el humor y las referencias a la actualidad.
```

Campos del frontmatter:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `title` | string | Nombre legible de la plataforma |
| `max_chars` | int | Límite de caracteres (0 = sin límite) |

El contenido del archivo son las instrucciones que recibirá el
Writer Agent para generar drafts. Incluye ejemplos del tono deseado.

## 2. Crear el Collector

Crea `backend/src/social_agent/collectors/<plataforma>.py`:

```python
from __future__ import annotations

from typing import Optional

from social_agent.collectors.base import BaseCollector, CollectedItem


class MiPlataformaCollector(BaseCollector):
    source_type = "social"  # o "rss", "webpage", etc.

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str,
        tags: list[str] | None = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(source_id, source_name, url, tags)
        self.api_key = api_key

    def fetch(self) -> list[CollectedItem]:
        if not self.api_key:
            return []
        # Llamar a la API de la plataforma y devolver CollectedItems
        # ...
        return items
```

### Registrar el collector

En `backend/src/social_agent/collectors/__init__.py`:

```python
from .mi_plataforma import MiPlataformaCollector
```

En `backend/src/social_agent/cli/commands.py`, función `_build_collector`:

```python
case SourceType.social:
    if "twitter" in source.url:
        return TwitterCollector(...)
    if "linkedin" in source.url:
        return LinkedInCollector(...)
    if "miplataforma" in source.url:
        return MiPlataformaCollector(
            source.id, source.name, source.url, source.tags,
            api_key=settings.miplataforma_api_key,
        )
```

También en `backend/src/social_agent/api/router_seeds.py`, misma función
`_build_collector`.

### Añadir credenciales a la configuración

En `backend/src/social_agent/config.py`:

```python
miplataforma_api_key: Optional[str] = None
```

## 3. Crear el Publisher

Crea `backend/src/social_agent/publishers/<plataforma>.py`:

```python
from __future__ import annotations

from social_agent.models.draft import Draft
from social_agent.publishers.base import BasePublisher, PublishResult


class MiPlataformaPublisher(BasePublisher):
    platform = "miplataforma"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def publish(self, draft: Draft) -> PublishResult:
        try:
            # Llamar a la API de publicación
            # ...
            post_id = "respuesta_de_la_api"
            return PublishResult(success=True, platform_post_id=post_id)
        except Exception as e:
            return PublishResult(success=False, error=str(e))
```

### Registrar el publisher

En `backend/src/social_agent/publishers/__init__.py`:

```python
from .mi_plataforma import MiPlataformaPublisher
```

En `backend/src/social_agent/api/router_publish.py`, función `_get_publisher`:

```python
def _get_publisher(platform: str) -> ...:
    if platform == "twitter":
        return TwitterPublisher(...)
    if platform == "linkedin":
        return LinkedInPublisher(...)
    if platform == "miplataforma":
        if not settings.miplataforma_api_key:
            return None
        return MiPlataformaPublisher(api_key=settings.miplataforma_api_key)
    return None
```

En `backend/src/social_agent/cli/commands.py`, comando `drafts_publish`:

```python
elif draft.platform == "miplataforma":
    if not settings.miplataforma_api_key:
        click.echo("MiPlataforma API key not configured.")
        return
    publisher = MiPlataformaPublisher(api_key=settings.miplataforma_api_key)
```

## 4. Tests

Crea o extiende archivos de test:

- `tests/test_collectors.py` — Test para `MiPlataformaCollector`
- `tests/test_publishers.py` — Test para `MiPlataformaPublisher`
- `tests/test_api.py` — Test del endpoint de publish (mockeando el publisher)

Ejemplo de test para publisher:

```python
from social_agent.models.draft import Draft
from social_agent.publishers.mi_plataforma import MiPlataformaPublisher


class TestMiPlataformaPublisher:
    def test_publish_success(self):
        publisher = MiPlataformaPublisher(api_key="test")
        draft = Draft(seed_id="s1", platform="miplataforma", content="Hello")
        result = publisher.publish(draft)
        assert result.success is True
        assert result.platform_post_id is not None
```

## Resumen del flujo completo

```
1. Prompt  →  Writer Agent genera drafts con el tono de la plataforma
2. Draft   →  Se aprueba manualmente
3. Publish →  Publisher envía el contenido a la API real
4. Collect →  Collector trae contenido de la plataforma como fuente de ideas
```
