from __future__ import annotations

import re

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.seed import Seed

from .base import BaseAgent

SYSTEM_PROMPT = """Eres un writer de contenido para redes sociales.

Tu trabajo es transformar ideas (seeds) en posts listos para publicar en una plataforma específica.

Reglas:
- Responde SOLO con el contenido del post, sin explicaciones ni markdown adicional.
- Sigue al pie de la letra las instrucciones de tono y estilo de la plataforma.
- No añadas hashtags a menos que la plataforma los requiera explícitamente.
- Encierra el post final entre las etiquetas <post> y </post>.
  Todo lo que esté fuera de esas etiquetas será ignorado."""


_THINKING_PREFIXES = (
    "we need to", "let me", "i'll", "i will",
    "the tone should", "avoid", "this should",
)


def _extract_post(text: str) -> str:
    m = re.search(r"<post>\s*(.*?)\s*</post>", text, re.DOTALL)
    if m:
        return m.group(1)

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
        seed: Seed,
        platform: str,
        platform_instructions: str,
        platform_name: str = "",
        max_chars: int = 0,
        dry_run: bool = False,
    ) -> Draft | str:
        url_str = seed.source_url or "(none)"

        user_prompt = (
            f"## Idea / Seed\n\n"
            f"Título: {seed.title}\n"
            f"Resumen: {seed.summary}\n"
            f"URL original: {url_str}\n\n"
            f"## Instrucciones de plataforma\n\n"
            f"{platform_instructions}\n\n"
            f"## Tarea\n\n"
            f"Genera un post para {platform_name or platform} basado en la idea anterior.\n"
            f"Respeta el límite de caracteres.\n"
            f"Envuelve el post final entre <post> y </post>."
        )

        response = self.run(user_prompt, max_tokens=4096)

        if dry_run:
            return response

        content = _extract_post(response)
        if max_chars and len(content) > max_chars:
            content = content[:max_chars].rsplit(" ", 1)[0]

        return Draft(
            seed_id=seed.id,
            platform=platform,
            content=content,
            status=DraftStatus.draft,
        )
