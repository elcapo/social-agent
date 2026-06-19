from __future__ import annotations

from typing import Optional

from litellm import completion as litellm_completion

from .config import settings


def llm_complete(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    raw: bool = False,
    response_format: Optional[dict] = None,
) -> str:
    model = model or settings.llm_provider
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if settings.llm_api_key:
        kwargs["api_key"] = settings.llm_api_key
    if settings.llm_base_url:
        kwargs["api_base"] = settings.llm_base_url
    if response_format is not None:
        kwargs["response_format"] = response_format

    response = litellm_completion(**kwargs)
    msg = response.choices[0].message

    content = msg.content or ""

    return response if raw else content
