from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed

from .base import BaseAgent


def _extract_json(text: str) -> dict | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


SYSTEM_PROMPT = """Actúa como un ideador de contenido para redes sociales.

Tu trabajo es generar una idea para un post a partir de:

1. El contenido de un artículo (semilla).
2. Los intereses del usuario.

Sigue estas reglas:

- La idea debe estar basada exclusivamente en el contenido del artículo proporcionado.
- Escribe directamente una versión resumida, sin empezar por "el artículo habla sobre...".
- Debe ser relevante a los intereses del usuario.
- No inventes nombres, cifras, empresas, productos ni detalles técnicos.
- Responde solo con un objeto JSON, sin markdown, ni explicaciones.
- El objeto debe tener: title (string) y summary (string).
- El campo summary debe ser un resumen fiel del contenido original, sin adornos ni reelaboración.
- El campo title debe ser un titular atractivo que capture la esencia de la idea."""


USER_TEMPLATE = """## Intereses del usuario

{interests}

## Artículo

Título: {title}
URL: {url}

{content}

Genera una idea detallada para un post basada en este artículo.
Escríbela en español aunque el idioma de la noticia sea otro.
Devuelve solo un objeto JSON con title y summary."""


class IdeatorAgent(BaseAgent):
    system_prompt = SYSTEM_PROMPT

    def generate_idea(
        self,
        seed: Seed,
        interests: str,
        dry_run: bool = False,
    ) -> Idea | str:
        user_prompt = USER_TEMPLATE.format(
            interests=interests,
            title=seed.title,
            url=seed.source_url or "(no URL)",
            content=seed.content,
        )

        response = self.run(user_prompt, max_tokens=2048)
        if dry_run:
            return response

        data = _extract_json(response)
        if data is None:
            return None

        return Idea(
            seed_id=seed.id,
            title=data.get("title", "Untitled"),
            summary=data.get("summary", ""),
            source_url=seed.source_url,
            status=IdeaStatus.pending,
            created_at=datetime.now(timezone.utc),
        )
