from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from social_agent.collectors.base import CollectedItem
from social_agent.models.seed import Seed, SeedStatus

from .base import BaseAgent


def _extract_json(text: str) -> list[dict] | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    m = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return None


SYSTEM_PROMPT = """Eres un ideator de contenido para redes sociales.

Tu trabajo es generar ideas para posts a partir de:
1. Una lista de intereses del usuario
2. Contenido recolectado de sus fuentes de información

Reglas:
- Cada idea debe estar directamente conectada al contenido proporcionado.
- Las ideas deben ser relevantes a los intereses del usuario.
- Genera ideas variadas, no repitas el mismo ángulo.
- Responde SOLO con una lista de objetos JSON, sin markdown ni explicaciones.
- Cada objeto debe tener: title, summary, tags (lista de strings), source_index (int).
- source_index es el índice del contenido del que deriva la idea (el que está entre corchetes)."""


USER_TEMPLATE = """## Intereses del usuario

{interests}

## Contenido recolectado

{collected}

Genera entre 3 y 5 ideas para posts basadas en el contenido anterior."""


class IdeatorAgent(BaseAgent):
    system_prompt = SYSTEM_PROMPT
    MAX_TOTAL_ITEMS = 50

    def _sort_key(self, item: CollectedItem) -> str:
        return item.published.isoformat() if item.published else ""

    def generate_seeds(
        self,
        interests: str,
        collected_items: list[CollectedItem],
        dry_run: bool = False,
    ) -> list[Seed] | str:
        items = sorted(collected_items, key=self._sort_key, reverse=True)
        items = items[: self.MAX_TOTAL_ITEMS]

        def _format_item(idx: int, item: CollectedItem) -> str:
            return (
                f"--- [{idx}] {item.title} ({item.source_name}) ---\n"
                f"URL: {item.url}\n"
                f"{item.content[:500]}"
            )

        collected_text = "\n\n".join(
            _format_item(i, item) for i, item in enumerate(items, start=1)
        )

        user_prompt = USER_TEMPLATE.format(
            interests=interests,
            collected=collected_text,
        )

        response = self.run(user_prompt, max_tokens=4096)
        if dry_run:
            return response

        data = _extract_json(response)
        if data is None:
            return []

        seeds: list[Seed] = []

        for entry in data:
            idx = entry.get("source_index")
            src_id: str | None = None
            src_url: str | None = None
            if isinstance(idx, int) and 1 <= idx <= len(items):
                src = items[idx - 1]
                src_id = src.source_id
                src_url = src.url

            seeds.append(
                Seed(
                    title=entry.get("title", "Untitled"),
                    summary=entry.get("summary", ""),
                    tags=entry.get("tags", []),
                    source_id=src_id,
                    source_url=src_url,
                    status=SeedStatus.pending,
                    created_at=datetime.now(timezone.utc),
                )
            )

        return seeds
