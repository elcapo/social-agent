from __future__ import annotations

import json
import re

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea

from .base import BaseAgent

SYSTEM_PROMPT = """Eres un writer de contenido para redes sociales.

Tu trabajo es transformar ideas en posts listos para publicar en una plataforma específica.

Reglas:
- Responde SIEMPRE en JSON con el campo "post" que contenga únicamente el contenido del post.
- No incluyas ningún otro texto fuera del JSON.
- Sigue al pie de la letra las instrucciones de tono y estilo de la plataforma.
- No añadas hashtags a menos que la plataforma los requiera explícitamente.

Distingue siempre entre las dos fuentes de input que puedes recibir:
- El "Resumen de la noticia" son hechos verificables extraídos fielemente del
  artículo original por el ideator. Trátalos como datos: no los adornes ni
  inventes detalles.
- El "Comentario del autor" es la voz del usuario: contexto personal,
  opiniones o instrucciones de enfoque (p. ej. "empieza narrando la publicación
  del modelo"). Intégralo en el tono y enfoque del post, pero no presentes las
  opiniones del usuario como hechos de la noticia."""


_URL_RE = re.compile(r'https?://[^\s]+')


def _effective_length(text: str) -> int:
    urls = _URL_RE.findall(text)
    return len(text) + sum(23 - len(u) for u in urls)


def _parse_post(text: str) -> str:
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "post" in data:
            return data["post"].strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return text.strip()


def _truncate_to_max_chars(content: str, max_chars: int) -> str:
    urls = _URL_RE.findall(content)
    if not urls:
        return content[:max_chars].rsplit(" ", 1)[0]
    diff = sum(len(u) - 23 for u in urls)
    raw_limit = max_chars + diff
    if raw_limit <= 0:
        return content[:max_chars]
    truncated = content[:raw_limit].rsplit(" ", 1)[0]
    return truncated


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
    ) -> Draft | str | None:
        url_str = idea.source_url or "(none)"

        char_limit = max_chars if max_chars else "sin límite"
        user_prompt = (
            f"## Idea\n\n"
            f"Título: {idea.title}\n"
            f"Resumen de la noticia (fiel al artículo original): {idea.summary}\n"
            f"URL original: {url_str}\n\n"
        )

        comment = (idea.comment or "").strip()
        if comment:
            user_prompt += (
                "## Comentario del autor "
                "(contexto e instrucciones propias, no parte de la noticia)\n\n"
                f"{comment}\n\n"
            )

        user_prompt += (
            f"## Instrucciones de plataforma\n\n"
            f"{platform_instructions}\n\n"
            f"## Tarea\n\n"
            f"Genera un post para {platform_name or platform} basado en la idea anterior.\n"
            f"Límite de caracteres (las URLs cuentan como 23): {char_limit}\n"
            f"Responde en JSON con el formato: {{\"post\": \"<contenido del post>\"}}"
        )

        response = self.run(user_prompt, max_tokens=4096, response_format={"type": "json_object"})

        if dry_run:
            return response

        content = _parse_post(response)

        if not content:
            response = self.run(user_prompt, max_tokens=4096, response_format={"type": "json_object"}, temperature=0.9)
            content = _parse_post(response)
            if not content:
                return None

        if max_chars and _effective_length(content) > max_chars:
            content = _truncate_to_max_chars(content, max_chars)

        return Draft(
            idea_id=idea.id,
            platform=platform,
            content=content,
            status=DraftStatus.draft,
        )
