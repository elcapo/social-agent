from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, CollectedItem


class WebScraperCollector(BaseCollector):
    source_type = "webpage"

    def fetch(self) -> list[CollectedItem]:
        response = httpx.get(self.url, follow_redirects=True, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)

        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else ""

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines[:200])

        return [
            CollectedItem(
                title=title,
                content=text,
                url=str(response.url),
                source_id=self.source_id,
                source_name=self.source_name,
                tags=self.tags,
            )
        ]
