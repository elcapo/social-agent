import re
from unittest.mock import MagicMock, patch

import httpx
from social_agent.collectors.base import BaseCollector, CollectedItem
from social_agent.collectors.link_scraper import LinkScraperCollector
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

    def test_fetch_empty_elements(self):
        c = LinkedInCollector("s1", "Test", "https://linkedin.com/in/user", access_token="tok")
        c.author_urn = "urn:li:person:abc"

        mock_resp = MagicMock(
            status_code=200,
            json=lambda: {"elements": []},
        )

        with patch("social_agent.collectors.social.httpx.get", return_value=mock_resp):
            items = c.fetch()

        assert items == []

    def test_fetch_no_commentary(self):
        c = LinkedInCollector("s1", "Test", "https://linkedin.com/in/user", access_token="tok")
        c.author_urn = "urn:li:person:abc"

        mock_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "elements": [
                    {"id": "post1"},
                    {"id": "post2", "commentary": ""},
                ]
            },
        )

        with patch("social_agent.collectors.social.httpx.get", return_value=mock_resp):
            items = c.fetch()

        assert len(items) == 2
        assert items[0].title == "(no text)"
        assert items[1].title == "(no text)"


class TestLinkedInCollectorFetchWithoutUrn:
    def test_fetch_resolves_urn_and_gets_posts(self):
        c = LinkedInCollector("s1", "Test", "https://linkedin.com/in/user", access_token="tok")

        mock_userinfo = MagicMock(
            status_code=200,
            json=lambda: {"sub": "member_123"},
        )
        mock_posts = MagicMock(
            status_code=200,
            json=lambda: {
                "elements": [
                    {"id": "p1", "commentary": "Post text"},
                ]
            },
        )

        with patch("social_agent.collectors.social.httpx.get") as mock_get:
            mock_get.side_effect = [mock_userinfo, mock_posts]
            items = c.fetch()

        assert len(items) == 1
        assert items[0].content == "Post text"
        assert c.author_urn == "urn:li:person:member_123"


LISTING_HTML = """\
<html><body>
  <nav><a href="/about">About Us</a></nav>
  <main>
    <article>
      <a href="/blog/post-1">Post One</a>
      <span class="date">2026-01-01</span>
    </article>
    <article>
      <a href="/blog/post-2">Post Two</a>
      <span class="date">2026-01-02</span>
    </article>
    <article>
      <a href="/blog/post-3">Post Three</a>
      <span class="date">2026-01-03</span>
    </article>
  </main>
  <footer><a href="/contact">Contact</a></footer>
</body></html>
"""

ARTICLE_HTML = """\
<html><body>
  <nav><a href="/">Home</a></nav>
  <article>
    <h1>Article Title</h1>
    <p>This is the full content of the article.</p>
    <p>More details here.</p>
  </article>
  <footer>Footer stuff</footer>
</body></html>
"""

MIXED_LINKS_HTML = """\
<html><body>
  <a href="/">Home</a>
  <a href="/blog/first-post">First Post</a>
  <a href="/pricing">Pricing</a>
  <a href="/blog/second-post">Second Post</a>
  <a href="/about">About</a>
  <a href="/category/tech">Tech Category</a>
</body></html>
"""


class TestLinkScraperCollector:
    def test_fetch_extracts_article_links(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog")
        c.url_pattern = re.compile(r"/blog/.+")

        responses = [
            MagicMock(status_code=200, text=LISTING_HTML),
            MagicMock(status_code=200, text=ARTICLE_HTML),
            MagicMock(status_code=200, text=ARTICLE_HTML),
            MagicMock(status_code=200, text=ARTICLE_HTML),
        ]

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.side_effect = responses
            items = c.fetch()

        assert len(items) == 3
        assert items[0].title == "Post One"
        assert items[1].title == "Post Two"
        assert items[2].title == "Post Three"

    def test_fetch_full_content(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog", config={"full_content": True})
        c.url_pattern = re.compile(r"/blog/.+")

        responses = [
            MagicMock(status_code=200, text=LISTING_HTML),
            MagicMock(status_code=200, text=ARTICLE_HTML),
            MagicMock(status_code=200, text=ARTICLE_HTML),
            MagicMock(status_code=200, text=ARTICLE_HTML),
        ]

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.side_effect = responses
            items = c.fetch()

        assert len(items) == 3
        assert "full content" in items[0].content.lower()

    def test_fetch_filters_by_url_pattern(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog", config={"full_content": False})
        c.url_pattern = re.compile(r"/blog/.+")

        responses = [
            MagicMock(status_code=200, text=MIXED_LINKS_HTML),
        ]

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.side_effect = responses
            items = c.fetch()

        assert len(items) == 2
        assert items[0].title == "First Post"
        assert items[1].title == "Second Post"

    def test_fetch_default_pattern_from_url(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog/")
        assert c._default_pattern("https://example.com/blog/").pattern == r"^/blog/.+"

    def test_fetch_custom_url_pattern_from_config(self):
        c = LinkScraperCollector(
            "s1", "Test", "https://example.com",
            config={"url_pattern": "/article/\\d+"},
        )
        assert c._build_pattern("https://example.com").pattern == "/article/\\d+"

    def test_fetch_max_items(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog", config={"max_items": 2, "full_content": False})
        c.url_pattern = re.compile(r"/blog/.+")

        listing_10 = LISTING_HTML.replace(
            "</article>",
            "</article>\n<article><a href=\"/blog/post-4\">Post Four</a></article>",
        )

        responses = [
            MagicMock(status_code=200, text=listing_10),
        ]

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.side_effect = responses
            items = c.fetch()

        assert len(items) == 2

    def test_fetch_empty_listing(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog")
        c.url_pattern = re.compile(r"/blog/.+")

        empty_html = "<html><body><p>No articles here</p></body></html>"

        responses = [
            MagicMock(status_code=200, text=empty_html),
        ]

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.side_effect = responses
            items = c.fetch()

        assert items == []

    def test_fetch_http_error_returns_empty(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog")

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock(status_code=500),
            )
            items = c.fetch()

        assert items == []

    def test_fetch_deduplicates_urls(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog", config={"full_content": False})
        c.url_pattern = re.compile(r"/blog/.+")

        dup_html = """\
<html><body>
  <a href="/blog/post-1">First Post</a>
  <a href="/blog/post-1">First Post (duplicate link)</a>
  <a href="/blog/post-2">Second Post</a>
</body></html>
"""

        responses = [
            MagicMock(status_code=200, text=dup_html),
        ]

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.side_effect = responses
            items = c.fetch()

        assert len(items) == 2

    def test_renderer_defaults_to_httpx(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com")
        assert c.renderer == "httpx"

    def test_renderer_playwright_from_config(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com", config={"renderer": "playwright"})
        assert c.renderer == "playwright"

    def test_renderer_httpx_fetch_page(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com")
        html = "<html><body><p>Hello httpx</p></body></html>"
        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200, text=html,
                url=MagicMock(__str__=lambda s: "https://example.com"),
            )
            soup, url = c._fetch_page("https://example.com")
        assert "Hello httpx" in soup.get_text()

    def test_renderer_playwright_raises_if_not_installed(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com", config={"renderer": "playwright"})
        with patch.dict("sys.modules", {"playwright": None}):
            import sys
            if "playwright" in sys.modules:
                del sys.modules["playwright"]
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                try:
                    c._fetch_page("https://example.com")
                    assert False, "Should have raised"
                except ImportError as e:
                    assert "playwright" in str(e).lower()

    def test_browser_closed_after_fetch(self):
        c = LinkScraperCollector("s1", "Test", "https://example.com/blog", config={"renderer": "playwright", "full_content": False})
        c.url_pattern = re.compile(r"/blog/.+")

        with patch("social_agent.collectors.link_scraper.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text=LISTING_HTML)
            items = c.fetch()

        assert c._browser is None
        assert items == []
