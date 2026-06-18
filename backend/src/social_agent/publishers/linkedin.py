from __future__ import annotations

from io import BytesIO
from typing import Optional

import httpx
from PIL import Image

from social_agent.media import prepare_media
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

    def _upload_image(self, author: str, source: str) -> str:
        data = prepare_media(source)

        try:
            fmt = Image.open(BytesIO(data)).format or "PNG"
            content_type = f"image/{fmt.lower()}"
        except Exception:
            content_type = "application/octet-stream"

        register_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        register_resp = httpx.post(
            f"{LINKEDIN_API_BASE}/rest/images?action=initializeUpload",
            headers=register_headers,
            json={"initializeUploadRequest": {"owner": author}},
        )
        register_resp.raise_for_status()
        reg_data = register_resp.json()
        upload_url = reg_data["value"]["uploadUrl"]
        image_urn = reg_data["value"]["image"]

        upload_resp = httpx.put(
            upload_url,
            headers={"Content-Type": content_type},
            content=data,
            follow_redirects=True,
        )
        upload_resp.raise_for_status()

        return image_urn

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

        all_sources = draft.media_urls + draft.media_paths
        if all_sources:
            try:
                image_urn = self._upload_image(author, all_sources[0])
                payload["content"] = {
                    "media": {
                        "title": "",
                        "id": image_urn,
                    }
                }
            except Exception as e:
                return PublishResult(
                    success=False,
                    error=f"Failed to upload image to LinkedIn: {e}",
                )

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
