from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, CollectedItem


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
        self._browser = None

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
        article = soup.find("article") or soup.find("main")
        container = article or soup.find("body")
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

    def _fetch_page_httpx(self, url: str) -> tuple[BeautifulSoup, str]:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup, str(response.url)

    def _fetch_page_playwright(self, url: str) -> tuple[BeautifulSoup, str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for renderer='playwright'. "
                "Install it with: uv pip install playwright && python -m playwright install chromium"
            )

        if self._browser is None:
            self._pw = sync_playwright().start()
            try:
                self._browser = self._pw.chromium.launch(headless=True)
            except Exception:
                self._pw.stop()
                raise

        page = self._browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            final_url = page.url
        finally:
            page.close()

        soup = BeautifulSoup(html, "html.parser")
        return soup, final_url

    def _fetch_page(self, url: str) -> tuple[BeautifulSoup, str]:
        if self.renderer == "playwright":
            return self._fetch_page_playwright(url)
        return self._fetch_page_httpx(url)

    def _close_browser(self) -> None:
        if hasattr(self, "_pw"):
            try:
                self._pw.stop()
            except Exception:
                pass
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

    def _fetch_article(self, url: str) -> str:
        try:
            soup, _ = self._fetch_page(url)
            return self._extract_content(soup)
        except Exception:
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

    def _do_fetch(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        try:
            soup, resolved_url = self._fetch_page(self.url)
        except Exception:
            return items

        pattern = self._build_pattern(resolved_url)
        links = self._extract_links(soup, resolved_url, pattern)

        collected_urls = set()
        for link in links:
            if len(items) >= self.max_items:
                break
            if link["url"] in collected_urls:
                continue
            collected_urls.add(link["url"])

            content = ""
            if self.full_content:
                content = self._fetch_article(link["url"])

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

        next_url = self._next_page_url(soup, resolved_url)
        while next_url and len(items) < self.max_items:
            try:
                soup, resolved_next = self._fetch_page(next_url)
            except Exception:
                break
            more_links = self._extract_links(soup, resolved_next, pattern)
            for link in more_links:
                if len(items) >= self.max_items:
                    break
                if link["url"] in collected_urls:
                    continue
                collected_urls.add(link["url"])

                content = ""
                if self.full_content:
                    content = self._fetch_article(link["url"])

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
            next_url = self._next_page_url(soup, resolved_next)

        return items[: self.max_items]
