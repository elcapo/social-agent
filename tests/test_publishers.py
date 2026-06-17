from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import tweepy
from social_agent.models.draft import Draft, DraftStatus
from social_agent.publishers.base import BasePublisher, PublishResult
from social_agent.publishers.linkedin import LinkedInPublisher
from social_agent.publishers.twitter import TwitterPublisher


class _DummyPublisher(BasePublisher):
    platform = "dummy"

    def publish(self, draft: Draft) -> PublishResult:
        return PublishResult(success=True, platform_post_id="dummy_123")


class TestBasePublisher:
    def test_interface(self):
        p = _DummyPublisher()
        assert p.platform == "dummy"
        result = p.publish(Draft(seed_id="s1", platform="dummy", content="hello"))
        assert result.success is True
        assert result.platform_post_id == "dummy_123"


class TestPublishResult:
    def test_defaults(self):
        r = PublishResult(success=True)
        assert r.success is True
        assert r.platform_post_id is None
        assert r.error is None
        assert r.published_at is not None

    def test_full(self):
        r = PublishResult(success=False, platform_post_id=None, error="boom")
        assert r.success is False
        assert r.error == "boom"


class TestTwitterPublisher:
    def test_publish_success(self):
        mock_client = MagicMock(spec=tweepy.Client)
        mock_response = MagicMock()
        mock_response.data = {"id": 987654}
        mock_client.create_tweet.return_value = mock_response

        publisher = TwitterPublisher("ck", "cs", "at", "ats")
        publisher.client = mock_client

        draft = Draft(seed_id="s1", platform="twitter", content="Hello world")
        result = publisher.publish(draft)

        assert result.success is True
        assert result.platform_post_id == "987654"
        mock_client.create_tweet.assert_called_once_with(text="Hello world")

    def test_publish_no_id_in_response(self):
        mock_client = MagicMock(spec=tweepy.Client)
        mock_response = MagicMock()
        mock_response.data = {}
        mock_client.create_tweet.return_value = mock_response

        publisher = TwitterPublisher("ck", "cs", "at", "ats")
        publisher.client = mock_client

        draft = Draft(seed_id="s1", platform="twitter", content="Hello")
        result = publisher.publish(draft)

        assert result.success is False
        assert "No tweet ID" in result.error

    def test_publish_tweepy_exception(self):
        mock_client = MagicMock(spec=tweepy.Client)
        mock_client.create_tweet.side_effect = tweepy.TweepyException("Rate limit")

        publisher = TwitterPublisher("ck", "cs", "at", "ats")
        publisher.client = mock_client

        draft = Draft(seed_id="s1", platform="twitter", content="Hello")
        result = publisher.publish(draft)

        assert result.success is False
        assert "Rate limit" in result.error


class TestLinkedInPublisher:
    def test_publish_success(self, tmp_path):
        draft = Draft(seed_id="s1", platform="linkedin", content="Post content")

        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {"sub": "abc123"},
            )
            with patch.object(httpx, "post") as mock_post:
                mock_post.return_value = MagicMock(
                    status_code=201,
                    headers={"x-restli-id": "urn:li:post:xyz"},
                    json=lambda: {},
                )

                publisher = LinkedInPublisher(access_token="tok")
                result = publisher.publish(draft)

        assert result.success is True
        assert result.platform_post_id == "urn:li:post:xyz"

    def test_publish_with_custom_author_urn(self):
        draft = Draft(seed_id="s1", platform="linkedin", content="Post content")

        with patch.object(httpx, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=201,
                headers={"x-restli-id": "urn:li:post:456"},
                json=lambda: {},
            )

            publisher = LinkedInPublisher(
                access_token="tok",
                author_urn="urn:li:person:custom",
            )
            result = publisher.publish(draft)

        assert result.success is True
        assert result.platform_post_id == "urn:li:post:456"

    def test_publish_auth_failure(self):
        draft = Draft(seed_id="s1", platform="linkedin", content="Post content")

        with patch.object(httpx, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            )

            publisher = LinkedInPublisher(access_token="bad_token")
            result = publisher.publish(draft)

        assert result.success is False
        assert "Failed to resolve" in result.error

    def test_publish_api_error(self, tmp_path):
        draft = Draft(seed_id="s1", platform="linkedin", content="Post content")

        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {"sub": "abc123"},
            )
            with patch.object(httpx, "post") as mock_post:
                mock_post.side_effect = httpx.HTTPStatusError(
                    "403 Forbidden",
                    request=MagicMock(),
                    response=MagicMock(status_code=403, json=lambda: {"message": "Forbidden"}),
                )

                publisher = LinkedInPublisher(access_token="tok")
                result = publisher.publish(draft)

        assert result.success is False
        assert "403" in result.error


class TestDraftPublishModel:
    def test_draft_defaults(self):
        d = Draft(seed_id="s1", platform="twitter", content="hello")
        assert d.platform_post_id is None
        assert d.publish_error is None
        assert d.publish_attempts == 0

    def test_draft_frontmatter_roundtrip(self):
        d = Draft(
            seed_id="s1",
            platform="twitter",
            content="hello",
            status=DraftStatus.published,
            platform_post_id="123",
            publish_error=None,
            publish_attempts=1,
        )
        fm = d.to_frontmatter()
        restored = Draft.from_frontmatter(fm)
        assert restored.platform_post_id == "123"
        assert restored.publish_attempts == 1
        assert restored.status == DraftStatus.published

    def test_draft_failed_status(self):
        d = Draft(
            seed_id="s1",
            platform="twitter",
            content="hello",
            status=DraftStatus.failed,
            publish_error="API error",
        )
        assert d.status == DraftStatus.failed
        assert d.publish_error == "API error"
