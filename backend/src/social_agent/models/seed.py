from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SeedStatus(str, Enum):
    pending = "pending"
    used = "used"
    discarded = "discarded"


class Seed(BaseModel):
    id: str = Field(default_factory=lambda: f"seed_{_utcnow().timestamp():.6f}")
    title: str
    summary: str
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    status: SeedStatus = SeedStatus.pending
    created_at: datetime = Field(default_factory=_utcnow)

    def to_frontmatter(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_frontmatter(cls, data: dict) -> Seed:
        data["status"] = SeedStatus(data["status"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
