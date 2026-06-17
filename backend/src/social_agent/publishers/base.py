from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from social_agent.models.draft import Draft


@dataclass
class PublishResult:
    success: bool
    platform_post_id: Optional[str] = None
    error: Optional[str] = None
    published_at: datetime = datetime.now(timezone.utc)


class BasePublisher(ABC):
    platform: str = ""

    @abstractmethod
    def publish(self, draft: Draft) -> PublishResult:
        ...
