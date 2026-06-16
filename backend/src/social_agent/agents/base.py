from __future__ import annotations

from abc import ABC

from ..llm import llm_complete


class BaseAgent(ABC):
    system_prompt: str = ""

    def run(self, user_prompt: str) -> str:
        return llm_complete(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )
