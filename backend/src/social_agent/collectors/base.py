from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CollectedItem:
    title: str
    content: str
    url: str
    source_id: str
    source_name: str
    published: Optional[datetime] = None
    collected_at: datetime = datetime.now(timezone.utc)
    tags: list[str] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []


class BaseCollector(ABC):
    source_type: str = ""

    def __init__(self, source_id: str, source_name: str, url: str, tags: list[str] | None = None):
        self.source_id = source_id
        self.source_name = source_name
        self.url = url
        self.tags = tags or []

    @abstractmethod
    def fetch(self) -> list[CollectedItem]:
        ...
