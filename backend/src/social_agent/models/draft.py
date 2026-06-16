from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DraftStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    rejected = "rejected"
    published = "published"


class Draft(BaseModel):
    id: str = Field(default_factory=lambda: f"draft_{_utcnow().timestamp():.6f}")
    seed_id: str
    platform: str
    content: str = ""
    status: DraftStatus = DraftStatus.draft
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    published_at: Optional[datetime] = None

    def to_frontmatter(self) -> dict:
        fm = {
            "id": self.id,
            "seed_id": self.seed_id,
            "platform": self.platform,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
        if self.published_at:
            fm["published_at"] = self.published_at.isoformat()
        return fm

    @classmethod
    def from_frontmatter(cls, data: dict) -> Draft:
        data["status"] = DraftStatus(data["status"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("published_at"):
            data["published_at"] = datetime.fromisoformat(data["published_at"])
        return cls(**data)
