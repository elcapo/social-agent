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
    failed = "failed"


class Draft(BaseModel):
    id: str = Field(default_factory=lambda: f"draft_{_utcnow().timestamp():.6f}")
    seed_id: str
    platform: str
    content: str = ""
    status: DraftStatus = DraftStatus.draft
    notes: Optional[str] = None
    platform_post_id: Optional[str] = None
    publish_error: Optional[str] = None
    publish_attempts: int = 0
    media_urls: list[str] = []
    media_paths: list[str] = []
    created_at: datetime = Field(default_factory=_utcnow)
    published_at: Optional[datetime] = None

    def to_frontmatter(self) -> dict:
        fm = {
            "id": self.id,
            "seed_id": self.seed_id,
            "platform": self.platform,
            "status": self.status.value,
            "notes": self.notes,
            "platform_post_id": self.platform_post_id,
            "publish_error": self.publish_error,
            "publish_attempts": self.publish_attempts,
            "media_urls": self.media_urls,
            "media_paths": self.media_paths,
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
        if not data.get("media_urls"):
            data["media_urls"] = []
        if not data.get("media_paths"):
            data["media_paths"] = []
        return cls(**data)
