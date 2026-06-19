from __future__ import annotations

import re

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea

from .base import BaseAgent

SYSTEM_PROMPT = """Eres un writer de contenido para redes sociales.

Tu trabajo es transformar ideas en posts listos para publicar en una plataforma específica.

Reglas:
- Responde SOLO con el contenido del post, sin explicaciones ni markdown adicional.
- Sigue al pie de la letra las instrucciones de tono y estilo de la plataforma.
- No añadas hashtags a menos que la plataforma los requiera explícitamente."""


_THINKING_PREFIXES = (
    "we need to", "let me", "i'll", "i will",
    "the tone should", "avoid", "this should",
)


def _extract_post(text: str) -> str:
    lines = text.strip().splitlines()
    cleaned: list[str] = []
    in_thinking = True
    for line in lines:
        stripped = line.strip().lower()
        if in_thinking and (
            any(stripped.startswith(p) for p in _THINKING_PREFIXES)
            or "seed idea" in stripped
            or not stripped
        ):
            continue
        in_thinking = False
        cleaned.append(line)

    result = "\n".join(cleaned).strip()
    return result if result else text.strip()


class WriterAgent(BaseAgent):
    system_prompt = SYSTEM_PROMPT

    def generate_draft(
        self,
        idea: Idea,
        platform: str,
        platform_instructions: str,
        platform_name: str = "",
        max_chars: int = 0,
        dry_run: bool = False,
    ) -> Draft | str:
        url_str = idea.source_url or "(none)"

        user_prompt = (
            f"## Idea\n\n"
            f"Título: {idea.title}\n"
            f"Resumen: {idea.summary}\n"
            f"URL original: {url_str}\n\n"
            f"## Instrucciones de plataforma\n\n"
            f"{platform_instructions}\n\n"
            f"## Tarea\n\n"
            f"Genera un post para {platform_name or platform} basado en la idea anterior.\n"
            f"Respeta el límite de caracteres."
        )

        response = self.run(user_prompt, max_tokens=4096)

        if dry_run:
            return response

        content = _extract_post(response)
        if max_chars and len(content) > max_chars:
            content = content[:max_chars].rsplit(" ", 1)[0]

        return Draft(
            idea_id=idea.id,
            platform=platform,
            content=content,
            status=DraftStatus.draft,
        )
