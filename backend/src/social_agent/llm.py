from __future__ import annotations

from typing import Optional

from litellm import completion as litellm_completion

from .config import settings


def llm_complete(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    model = model or settings.llm_provider
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if settings.llm_api_key:
        kwargs["api_key"] = settings.llm_api_key
    if settings.llm_base_url:
        kwargs["api_base"] = settings.llm_base_url

    response = litellm_completion(**kwargs)
    return response.choices[0].message.content or ""
