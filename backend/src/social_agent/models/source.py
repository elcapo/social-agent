from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    rss = "rss"
    webpage = "webpage"
    social = "social"
    manual = "manual"


class SourcePriority(int, Enum):
    high = 1
    medium = 2
    low = 3


class Source(BaseModel):
    id: str = Field(default_factory=lambda: f"src_{_utcnow().timestamp():.6f}")
    name: str
    source_type: SourceType
    url: str
    priority: SourcePriority = SourcePriority.medium
    tags: list[str] = []
    enabled: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    last_fetched: Optional[datetime] = None

    def to_frontmatter(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type.value,
            "url": self.url,
            "priority": self.priority.value,
            "tags": self.tags,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_fetched": self.last_fetched.isoformat() if self.last_fetched else None,
        }

    @classmethod
    def from_frontmatter(cls, data: dict) -> Source:
        data["source_type"] = SourceType(data["source_type"])
        data["priority"] = SourcePriority(data["priority"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_fetched"):
            data["last_fetched"] = datetime.fromisoformat(data["last_fetched"])
        return cls(**data)
