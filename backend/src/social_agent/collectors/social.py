from __future__ import annotations

from typing import Optional

import httpx

from .base import BaseCollector, CollectedItem

TWITTER_API_BASE = "https://api.twitter.com/2"


class TwitterCollector(BaseCollector):
    source_type = "social"

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str,
        tags: list[str] | None = None,
        bearer_token: Optional[str] = None,
    ):
        super().__init__(source_id, source_name, url, tags)
        self.bearer_token = bearer_token

    def fetch(self) -> list[CollectedItem]:
        if not self.bearer_token:
            return []

        username = self.url.strip("/").rsplit("/", 1)[-1]
        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        try:
            user_resp = httpx.get(
                f"{TWITTER_API_BASE}/users/by/username/{username}",
                headers=headers,
            )
            user_resp.raise_for_status()
            user_id = user_resp.json()["data"]["id"]

            tweets_resp = httpx.get(
                f"{TWITTER_API_BASE}/users/{user_id}/tweets",
                headers=headers,
                params={"max_results": 10, "tweet.fields": "created_at"},
            )
            tweets_resp.raise_for_status()
            tweets = tweets_resp.json().get("data", [])
        except Exception:
            return []

        items: list[CollectedItem] = []
        for t in tweets:
            items.append(
                CollectedItem(
                    title=t["text"][:80],
                    content=t["text"],
                    url=f"https://twitter.com/{username}/status/{t['id']}",
                    source_id=self.source_id,
                    source_name=self.source_name,
                    tags=self.tags,
                )
            )
        return items


LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_VERSION = "202401"


class LinkedInCollector(BaseCollector):
    source_type = "social"

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str,
        tags: list[str] | None = None,
        access_token: Optional[str] = None,
    ):
        super().__init__(source_id, source_name, url, tags)
        self.access_token = access_token
        self.author_urn = None

    def _resolve_author_urn(self) -> str:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": LINKEDIN_VERSION,
        }
        resp = httpx.get(
            f"{LINKEDIN_API_BASE}/rest/userinfo",
            headers=headers,
        )
        resp.raise_for_status()
        return f"urn:li:person:{resp.json()['sub']}"

    def fetch(self) -> list[CollectedItem]:
        if not self.access_token:
            return []

        try:
            if not self.author_urn:
                self.author_urn = self._resolve_author_urn()
        except Exception:
            return []

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        try:
            resp = httpx.get(
                f"{LINKEDIN_API_BASE}/rest/posts",
                headers=headers,
                params={"author": self.author_urn, "q": "author", "count": 10},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        items: list[CollectedItem] = []
        for post in data.get("elements", []):
            commentary = post.get("commentary", "")
            items.append(
                CollectedItem(
                    title=commentary[:80] if commentary else "(no text)",
                    content=commentary,
                    url=post.get("id", ""),
                    source_id=self.source_id,
                    source_name=self.source_name,
                    tags=self.tags,
                )
            )
        return items
