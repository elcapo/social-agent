from __future__ import annotations

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.seed import Seed

from .base import BaseAgent

SYSTEM_PROMPT = """Eres un writer de contenido para redes sociales.

Tu trabajo es transformar ideas (seeds) en posts listos para publicar en una plataforma específica.

Reglas:
- Responde SOLO con el contenido del post, sin explicaciones ni markdown adicional.
- Sigue al pie de la letra las instrucciones de tono y estilo de la plataforma.
- No añadas hashtags a menos que la plataforma los requiera explícitamente."""


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
        tags_str = ", ".join(seed.tags) if seed.tags else "(none)"

        user_prompt = (
            f"## Idea / Seed\n\n"
            f"Título: {seed.title}\n"
            f"Resumen: {seed.summary}\n"
            f"Tags: {tags_str}\n\n"
            f"## Instrucciones de plataforma\n\n"
            f"{platform_instructions}\n\n"
            f"## Tarea\n\n"
            f"Genera un post para {platform_name or platform} basado en la idea anterior.\n"
            f"Respeta el límite de caracteres. Responde SOLO con el contenido del post."
        )

        response = self.run(user_prompt, max_tokens=1024)

        if dry_run:
            return response

        content = response.strip()
        if max_chars and len(content) > max_chars:
            content = content[:max_chars].rsplit(" ", 1)[0]

        return Draft(
            seed_id=seed.id,
            platform=platform,
            content=content,
            status=DraftStatus.draft,
        )
