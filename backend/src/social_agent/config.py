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
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    linkedin_author_urn: Optional[str] = None

    data_dir: Path = Path("data")
    prompts_dir: Path = Path("data/prompts")


settings = Settings()
