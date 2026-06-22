from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
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

_MAX_WORKERS = 5


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
        self.max_items = self.config.get("max_items", self.MAX_ITEMS)

    def _fetch_article(
        self,
        url: str,
        browser: PlaywrightBrowser | None = None,
        client: httpx.Client | None = None,
    ) -> str:
        try:
            if browser is not None:
                soup, _ = browser.fetch_page(url)
            else:
                headers = {"User-Agent": _USER_AGENT}
                if client is not None:
                    response = client.get(url, headers=headers)
                else:
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
        # Truncate entries to max_items *before* fetching full content to avoid
        # downloading articles that will be discarded by the slice anyway.
        # Sort first by date (most recent first) so we keep the newest ones.
        entries = list(parsed.entries)
        entries.sort(key=_entry_sort_key, reverse=True)

        # Deduplicate entries by link within the same feed.
        seen_links: set[str] = set()
        unique_entries = []
        for entry in entries:
            link = entry.get("link", self.url)
            if link in seen_links:
                continue
            seen_links.add(link)
            unique_entries.append(entry)

        candidates = unique_entries[: self.max_items]

        if self.full_content and len(candidates) > 1 and browser is None:
            contents = self._fetch_articles_concurrent(candidates)
        else:
            contents = [
                self._fetch_article(entry.get("link", self.url), browser)
                if self.full_content
                else entry.get("summary", entry.get("description", ""))
                for entry in candidates
            ]

        items: list[CollectedItem] = []
        for entry, content in zip(candidates, contents):
            link = entry.get("link", self.url)
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
        return items

    def _fetch_articles_concurrent(self, entries: list[dict]) -> list[str]:
        """Fetch full article content for ``entries`` concurrently.

        Uses a shared ``httpx.Client`` for connection pooling and a
        ``ThreadPoolExecutor`` with ``_MAX_WORKERS`` workers. Results are
        returned in the same order as ``entries``. Network errors yield an
        empty string for that entry (mirroring ``_fetch_article``).
        """
        links = [entry.get("link", self.url) for entry in entries]
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
                futures = [
                    pool.submit(self._fetch_article, link, None, client)
                    for link in links
                ]
                return [f.result() for f in futures]


def _sort_key(item: CollectedItem) -> str:
    return item.published.isoformat() if item.published else ""


def _entry_sort_key(entry: dict) -> str:
    published = _parse_date(entry)
    return published.isoformat() if published else ""


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
