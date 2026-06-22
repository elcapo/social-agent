from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

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
    storage_backend: str = "markdown"
    sqlite_path: Optional[Path] = None

    timezone: str = "Europe/Madrid"


settings = Settings()


@lru_cache(maxsize=32)
def _zoneinfo(name: str) -> ZoneInfo:
    """Return a cached ``ZoneInfo`` for a given IANA timezone name."""
    return ZoneInfo(name)


def get_tz(name: Optional[str] = None) -> ZoneInfo:
    """Return the ``ZoneInfo`` for the configured timezone (or the given name).

    Reads ``settings.timezone`` at call time so tests that monkeypatch the
    setting see the updated value; the underlying ``ZoneInfo`` objects are
    cached by name (they are immutable).
    """
    return _zoneinfo(name or settings.timezone)
