from __future__ import annotations

from abc import ABC

from ..llm import llm_complete


class BaseAgent(ABC):
    system_prompt: str = ""

    def run(self, user_prompt: str, *, raw: bool = False, max_tokens: int | None = None) -> str:
        return llm_complete(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            raw=raw,
            max_tokens=max_tokens,
        )
