from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from social_agent.utils import html_to_markdown

from .base import BaseCollector, CollectedItem
from .playwright_utils import PlaywrightBrowser

logger = logging.getLogger(__name__)

_MAX_WORKERS = 5


def _fetch_page(url: str, renderer: str = "httpx") -> tuple[BeautifulSoup, str]:
    if renderer == "playwright":
        with PlaywrightBrowser() as browser:
            return browser.fetch_page(url)
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser"), str(response.url)


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title:
        title = soup.title.get_text(strip=True)
        if title:
            return title
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _extract_content_html(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    article = soup.find("article")
    if article and len(article.get_text(strip=True)) < 500:
        article = None
    container = article or soup.find("main") or soup.find("body")
    if container is None:
        return ""
    return str(container)


def scrape_url(url: str, renderer: str = "httpx") -> tuple[str, str]:
    """Fetch a single URL and return (title, content_markdown).

    Reuses the extraction logic of LinkScraperCollector for a one-off scrape
    without requiring a Source. Raises httpx.HTTPError on network failures.
    """
    soup, _ = _fetch_page(url, renderer=renderer)
    title = _extract_title(soup)
    html = _extract_content_html(soup)
    content = html_to_markdown(html) if html else ""
    return title, content


class LinkScraperCollector(BaseCollector):
    source_type = "link_scraper"

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
        self.max_items = self.config.get("max_items", 10)
        self.full_content = self.config.get("full_content", True)
        self.url_pattern = self.config.get("url_pattern")
        self.renderer = self.config.get("renderer", "httpx")
        self._browser: PlaywrightBrowser | None = None

    def _default_pattern(self, base_url: str) -> re.Pattern:
        path = httpx.URL(base_url).path.rstrip("/")
        if not path:
            return re.compile(r"")
        return re.compile(rf"^{re.escape(path)}/.+")

    def _build_pattern(self, base_url: str) -> re.Pattern:
        if self.url_pattern:
            return re.compile(self.url_pattern)
        return self._default_pattern(base_url)

    def _clean_soup(self, soup: BeautifulSoup) -> None:
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

    def _extract_content(self, soup: BeautifulSoup) -> str:
        self._clean_soup(soup)
        article = soup.find("article")
        if article and len(article.get_text(strip=True)) < 500:
            article = None
        container = article or soup.find("main") or soup.find("body")
        if container is None:
            return ""
        text = container.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines[:200])

    def _extract_links(self, soup: BeautifulSoup, base_url: str, pattern: re.Pattern) -> list[dict]:
        seen = set()
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            abs_url = urljoin(base_url, href)
            if abs_url in seen:
                continue
            if not pattern.search(abs_url):
                continue
            seen.add(abs_url)
            title = a.get_text(strip=True) or ""
            links.append({"url": abs_url, "title": title})
        return links

    def _fetch_page(self, url: str) -> tuple[BeautifulSoup, str]:
        if self.renderer == "playwright":
            if self._browser is None:
                self._browser = PlaywrightBrowser()
            return self._browser.fetch_page(url)
        return _fetch_page(url, "httpx")

    def _close_browser(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None

    def _fetch_article(self, url: str) -> str:
        try:
            soup, _ = self._fetch_page(url)
            return self._extract_content(soup)
        except Exception:
            logger.warning("Failed to fetch article %s", url, exc_info=True)
            return ""

    def _next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        next_link = soup.find("a", string=re.compile(r"(next|siguiente|›|»|→)", re.IGNORECASE))
        if next_link and next_link.get("href"):
            return urljoin(current_url, next_link["href"])
        rel_next = soup.find("link", rel="next")
        if rel_next and rel_next.get("href"):
            return urljoin(current_url, rel_next["href"])
        return None

    def fetch(self) -> list[CollectedItem]:
        try:
            return self._do_fetch()
        finally:
            self._close_browser()

    def _collect_links(
        self, soup: BeautifulSoup, resolved_url: str, pattern: re.Pattern,
    ) -> list[dict]:
        """Collect unique links across the listing page and any pagination."""
        collected: list[dict] = []
        collected_urls: set[str] = set()

        for link in self._extract_links(soup, resolved_url, pattern):
            if len(collected) >= self.max_items:
                return collected
            if link["url"] in collected_urls:
                continue
            collected_urls.add(link["url"])
            collected.append(link)

        next_url = self._next_page_url(soup, resolved_url)
        while next_url and len(collected) < self.max_items:
            try:
                soup, resolved_next = self._fetch_page(next_url)
            except Exception:
                break
            for link in self._extract_links(soup, resolved_next, pattern):
                if len(collected) >= self.max_items:
                    break
                if link["url"] in collected_urls:
                    continue
                collected_urls.add(link["url"])
                collected.append(link)
            next_url = self._next_page_url(soup, resolved_next)

        return collected[: self.max_items]

    def _fetch_articles_concurrent(self, urls: list[str]) -> list[str]:
        """Fetch article content for ``urls`` concurrently with a shared client.

        Playwright is not thread-safe, so when ``renderer == "playwright"`` this
        falls back to sequential fetching. Results are returned in the same
        order as ``urls``.
        """
        if self.renderer == "playwright" or len(urls) <= 1:
            return [self._fetch_article(url) for url in urls]

        with httpx.Client(follow_redirects=True, timeout=30) as client:
            with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
                futures = [
                    pool.submit(self._fetch_article_with_client, url, client)
                    for url in urls
                ]
                return [f.result() for f in futures]

    def _fetch_article_with_client(self, url: str, client: httpx.Client) -> str:
        try:
            response = client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            return self._extract_content(soup)
        except Exception:
            logger.warning("Failed to fetch article %s", url, exc_info=True)
            return ""

    def _do_fetch(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        try:
            soup, resolved_url = self._fetch_page(self.url)
        except Exception:
            logger.exception("Failed to fetch listing page %s", self.url)
            return items

        pattern = self._build_pattern(resolved_url)
        links = self._collect_links(soup, resolved_url, pattern)
        if not links:
            return items

        if self.full_content:
            contents = self._fetch_articles_concurrent([link["url"] for link in links])
        else:
            contents = [""] * len(links)

        for link, content in zip(links, contents):
            items.append(
                CollectedItem(
                    title=link["title"] or (content[:80] if content else link["url"]),
                    content=content or link["title"],
                    url=link["url"],
                    source_id=self.source_id,
                    source_name=self.source_name,
                    tags=self.tags,
                )
            )

        return items[: self.max_items]
