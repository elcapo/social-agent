from __future__ import annotations

from datetime import datetime, timezone

from social_agent.collectors.base import CollectedItem
from social_agent.models.seed import Seed, SeedStatus

from .base import BaseAgent

SYSTEM_PROMPT = """Eres un ideator de contenido para redes sociales.

Tu trabajo es generar ideas para posts a partir de:
1. Una lista de intereses del usuario
2. Contenido recolectado de sus fuentes de información

Reglas:
- Cada idea debe estar directamente conectada al contenido proporcionado.
- Las ideas deben ser relevantes a los intereses del usuario.
- Genera ideas variadas, no repitas el mismo ángulo.
- Responde SOLO con una lista de objetos JSON, sin markdown ni explicaciones.
- Cada objeto debe tener: title (string), summary (string), tags (lista de strings)."""


USER_TEMPLATE = """## Intereses del usuario

{interests}

## Contenido recolectado

{collected}

Genera entre 3 y 5 ideas para posts basadas en el contenido anterior."""


class IdeatorAgent(BaseAgent):
    system_prompt = SYSTEM_PROMPT

    def generate_seeds(
        self,
        interests: str,
        collected_items: list[CollectedItem],
    ) -> list[Seed]:
        import json

        collected_text = "\n\n".join(
            f"--- {item.title} ({item.source_name}) ---\n{item.content[:500]}"
            for item in collected_items
        )

        user_prompt = USER_TEMPLATE.format(
            interests=interests,
            collected=collected_text,
        )

        response = self.run(user_prompt)
        seeds: list[Seed] = []

        try:
            data = json.loads(response)
            if isinstance(data, dict):
                data = [data]
        except json.JSONDecodeError:
            import re

            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return seeds
            else:
                return seeds

        for item in data:
            seeds.append(
                Seed(
                    title=item.get("title", "Untitled"),
                    summary=item.get("summary", ""),
                    tags=item.get("tags", []),
                    status=SeedStatus.pending,
                    created_at=datetime.now(timezone.utc),
                )
            )

        return seeds
