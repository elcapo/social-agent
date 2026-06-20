from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdeaStatus(str, Enum):
    pending = "pending"
    used = "used"
    discarded = "discarded"


class Idea(BaseModel):
    id: str = Field(default_factory=lambda: f"idea_{_utcnow().timestamp():.6f}")
    seed_id: str
    title: str
    summary: str
    comment: Optional[str] = None
    source_url: Optional[str] = None
    status: IdeaStatus = IdeaStatus.pending
    created_at: datetime = Field(default_factory=_utcnow)

    def to_frontmatter(self) -> dict:
        return {
            "id": self.id,
            "seed_id": self.seed_id,
            "title": self.title,
            "summary": self.summary,
            "comment": self.comment,
            "source_url": self.source_url,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_frontmatter(cls, data: dict) -> Idea:
        data["status"] = IdeaStatus(data["status"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
