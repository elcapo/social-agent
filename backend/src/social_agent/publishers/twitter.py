from __future__ import annotations

import tempfile
from pathlib import Path

import tweepy

from social_agent.media import prepare_media
from social_agent.models.draft import Draft

from .base import BasePublisher, PublishResult


class TwitterPublisher(BasePublisher):
    platform = "twitter"

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
    ) -> None:
        self.client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        auth = tweepy.OAuth1UserHandler(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        self.api = tweepy.API(auth)

    def _upload_media(self, url_or_path: str) -> int:
        data = prepare_media(url_or_path)
        suffix = ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(data)
            tmp = f.name
        try:
            media = self.api.media_upload(filename=tmp)
            return media.media_id
        finally:
            Path(tmp).unlink(missing_ok=True)

    def publish(self, draft: Draft) -> PublishResult:
        kwargs = {"text": draft.content}
        all_sources = draft.media_urls + draft.media_paths
        if all_sources:
            media_ids = []
            for src in all_sources:
                try:
                    media_ids.append(self._upload_media(src))
                except Exception:
                    continue
            if media_ids:
                kwargs["media_ids"] = media_ids
        try:
            response = self.client.create_tweet(**kwargs)
            if response.data and "id" in response.data:
                return PublishResult(
                    success=True,
                    platform_post_id=str(response.data["id"]),
                )
            return PublishResult(
                success=False,
                error="No tweet ID returned from API",
            )
        except tweepy.TweepyException as e:
            return PublishResult(
                success=False,
                error=str(e),
            )
