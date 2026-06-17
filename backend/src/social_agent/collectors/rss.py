from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser

from .base import BaseCollector, CollectedItem


class RSSCollector(BaseCollector):
    source_type = "rss"
    MAX_ITEMS = 20

    def fetch(self) -> list[CollectedItem]:
        parsed = feedparser.parse(self.url)
        items: list[CollectedItem] = []

        for entry in parsed.entries:
            published = _parse_date(entry)
            items.append(
                CollectedItem(
                    title=entry.get("title", ""),
                    content=entry.get("summary", entry.get("description", "")),
                    url=entry.get("link", self.url),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    published=published,
                    tags=self.tags,
                )
            )

        items.sort(key=_sort_key, reverse=True)
        return items[: self.MAX_ITEMS]


def _sort_key(item: CollectedItem) -> str:
    return item.published.isoformat() if item.published else ""


def _parse_date(entry: dict) -> Optional[datetime]:
    for field in ("published", "updated", "created"):
        raw = entry.get(f"{field}_parsed")
        if raw:
            return datetime.fromtimestamp(time.mktime(raw), tz=timezone.utc)
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except (ValueError, TypeError):
                pass
    return None
