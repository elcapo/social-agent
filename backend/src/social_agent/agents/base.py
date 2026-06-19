from __future__ import annotations

from abc import ABC

from ..llm import llm_complete


class BaseAgent(ABC):
    system_prompt: str = ""

    def run(self, user_prompt: str, *, raw: bool = False, max_tokens: int | None = None, response_format: dict | None = None, temperature: float | None = None) -> str:
        kwargs = dict(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            raw=raw,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        if temperature is not None:
            kwargs["temperature"] = temperature
        return llm_complete(**kwargs)
