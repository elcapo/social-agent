from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, CollectedItem
from .playwright_utils import PlaywrightBrowser

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class RSSCollector(BaseCollector):
    source_type = "rss"
    MAX_ITEMS = 20

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str,
        tags: list[str] | None = None,
        config: dict | None = None,
    ):
        super().__init__(source_id, source_name, url, tags)
        self.config = config or {}
        self.full_content = self.config.get("full_content", False)
        self.renderer = self.config.get("renderer", "httpx")

    def _fetch_article(self, url: str, browser: PlaywrightBrowser | None = None) -> str:
        try:
            if browser is not None:
                soup, _ = browser.fetch_page(url)
            else:
                headers = {"User-Agent": _USER_AGENT}
                response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
        except Exception:
            return ""

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        container = soup.find("article")
        if container and len(container.get_text(strip=True)) < 500:
            container = None
        container = container or soup.find("main") or soup.find("body")
        if container is None:
            return ""

        return container.decode_contents()

    def fetch(self) -> list[CollectedItem]:
        parsed = feedparser.parse(self.url)

        if self.renderer == "playwright":
            with PlaywrightBrowser() as browser:
                return self._collect(parsed, browser)
        return self._collect(parsed)

    def _collect(
        self,
        parsed: object,
        browser: PlaywrightBrowser | None = None,
    ) -> list[CollectedItem]:
        items: list[CollectedItem] = []

        for entry in parsed.entries:
            link = entry.get("link", self.url)

            if self.full_content:
                content = self._fetch_article(link, browser)
            else:
                content = entry.get("summary", entry.get("description", ""))

            items.append(
                CollectedItem(
                    title=entry.get("title", ""),
                    content=content,
                    url=link,
                    source_id=self.source_id,
                    source_name=self.source_name,
                    published=_parse_date(entry),
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
