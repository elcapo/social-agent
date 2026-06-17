from __future__ import annotations

import tweepy

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

    def publish(self, draft: Draft) -> PublishResult:
        try:
            response = self.client.create_tweet(text=draft.content)
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
