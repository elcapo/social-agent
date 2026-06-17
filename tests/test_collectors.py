from unittest.mock import MagicMock, patch

import httpx
from social_agent.collectors.base import BaseCollector, CollectedItem
from social_agent.collectors.social import LinkedInCollector, TwitterCollector


class _DummyCollector(BaseCollector):
    source_type = "dummy"

    def fetch(self) -> list[CollectedItem]:
        return [
            CollectedItem(
                title="Test Item",
                content="Test content",
                url="https://example.com",
                source_id=self.source_id,
                source_name=self.source_name,
                tags=self.tags,
            )
        ]


class TestBaseCollector:
    def test_collector_interface(self):
        c = _DummyCollector("src_1", "Test", "https://example.com", ["tag1"])
        assert c.source_id == "src_1"
        assert c.source_name == "Test"
        assert c.source_type == "dummy"
        assert c.tags == ["tag1"]

    def test_fetch_returns_items(self):
        c = _DummyCollector("src_1", "Test", "https://example.com")
        items = c.fetch()
        assert len(items) == 1
        assert items[0].title == "Test Item"
        assert items[0].content == "Test content"

    def test_fetch_item_has_metadata(self):
        c = _DummyCollector("src_1", "Test", "https://example.com", ["tag_x"])
        items = c.fetch()
        item = items[0]
        assert item.source_id == "src_1"
        assert item.source_name == "Test"
        assert item.tags == ["tag_x"]
        assert item.collected_at is not None


class TestCollectedItem:
    def test_default_tags_is_empty_list(self):
        item = CollectedItem(
            title="T", content="C", url="https://e.com",
            source_id="s1", source_name="N",
        )
        assert item.tags == []

    def test_custom_tags(self):
        item = CollectedItem(
            title="T", content="C", url="https://e.com",
            source_id="s1", source_name="N",
            tags=["a", "b"],
        )
        assert item.tags == ["a", "b"]


class TestTwitterCollector:
    def test_fetch_no_bearer_token(self):
        c = TwitterCollector("s1", "Test", "https://twitter.com/user")
        items = c.fetch()
        assert items == []

    def test_fetch_success(self):
        c = TwitterCollector("s1", "Test", "https://twitter.com/elonmusk", bearer_token="tok")
        mock_user = MagicMock(json=lambda: {"data": {"id": "12345"}})
        mock_tweets = MagicMock(json=lambda: {"data": [
            {"id": "1", "text": "Hello world"},
            {"id": "2", "text": "Second tweet"},
        ]})

        with patch("social_agent.collectors.social.httpx.get") as mock_get:
            mock_get.side_effect = [mock_user, mock_tweets]
            items = c.fetch()

        assert len(items) == 2
        assert items[0].content == "Hello world"
        assert items[1].content == "Second tweet"
        assert items[0].url == "https://twitter.com/elonmusk/status/1"
        assert items[1].url == "https://twitter.com/elonmusk/status/2"

    def test_fetch_api_error(self):
        c = TwitterCollector("s1", "Test", "https://twitter.com/user", bearer_token="tok")

        with patch("social_agent.collectors.social.httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(),
                response=MagicMock(status_code=404),
            )

            items = c.fetch()
            # Error dentro de fetch propaga la excepción
            assert items == []


class TestLinkedInCollector:
    def test_fetch_no_access_token(self):
        c = LinkedInCollector("s1", "Test", "https://linkedin.com/in/user")
        items = c.fetch()
        assert items == []

    def test_fetch_success(self):
        c = LinkedInCollector("s1", "Test", "https://linkedin.com/in/user", access_token="tok")
        c.author_urn = "urn:li:person:abc"

        mock_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "elements": [
                    {"id": "post1", "commentary": "First post"},
                    {"id": "post2", "commentary": "Second post with more text"},
                ]
            },
        )

        with patch("social_agent.collectors.social.httpx.get", return_value=mock_resp):
            items = c.fetch()

        assert len(items) == 2
        assert items[0].title == "First post"
        assert items[0].content == "First post"
        assert items[1].content == "Second post with more text"

    def test_fetch_auth_failure(self):
        c = LinkedInCollector("s1", "Test", "https://linkedin.com/in/user", access_token="bad")

        with patch("social_agent.collectors.social.httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "401", request=MagicMock(),
                response=MagicMock(status_code=401),
            )
            items = c.fetch()

        assert items == []
