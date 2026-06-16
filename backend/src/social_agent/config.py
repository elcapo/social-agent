from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "SOCIAL_AGENT_", "env_file": ".env", "extra": "ignore"}

    llm_provider: str = "openai/gpt-4o"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None

    twitter_bearer_token: Optional[str] = None
    linkedin_access_token: Optional[str] = None

    data_dir: Path = Path("data")
    prompts_dir: Path = Path("data/prompts")


settings = Settings()
