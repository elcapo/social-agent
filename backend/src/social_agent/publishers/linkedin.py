from __future__ import annotations

from typing import Optional

import httpx

from social_agent.models.draft import Draft

from .base import BasePublisher, PublishResult

LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_VERSION = "202606"


class LinkedInPublisher(BasePublisher):
    platform = "linkedin"

    def __init__(self, access_token: str, author_urn: Optional[str] = None) -> None:
        self.access_token = access_token
        self.author_urn = author_urn

    def _get_person_urn(self) -> str:
        if self.author_urn:
            return self.author_urn
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        resp = httpx.get(
            f"{LINKEDIN_API_BASE}/v2/userinfo",
            headers=headers,
        )
        resp.raise_for_status()
        sub = resp.json()["sub"]
        return f"urn:li:person:{sub}"

    def publish(self, draft: Draft) -> PublishResult:
        try:
            author = self._get_person_urn()
        except Exception as e:
            return PublishResult(
                success=False,
                error=f"Failed to resolve LinkedIn author URN: {e}",
            )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        payload = {
            "author": author,
            "commentary": draft.content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
        }

        try:
            resp = httpx.post(
                f"{LINKEDIN_API_BASE}/rest/posts",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            post_id = resp.headers.get("x-restli-id")
            return PublishResult(
                success=True,
                platform_post_id=post_id,
            )
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                detail = e.response.json()
            except Exception:
                detail = e.response.text
            return PublishResult(
                success=False,
                error=f"HTTP {e.response.status_code}: {detail}",
            )
        except httpx.RequestError as e:
            return PublishResult(
                success=False,
                error=f"Request failed: {e}",
            )
