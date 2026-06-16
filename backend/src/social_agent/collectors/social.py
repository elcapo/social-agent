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

    def fetch(self) -> list[CollectedItem]:
        if not self.access_token:
            return []
        return []
