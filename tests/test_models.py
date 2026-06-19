from datetime import datetime, timezone

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourcePriority, SourceType


class TestSource:
    def test_create_source(self):
        src = Source(name="Test RSS", source_type=SourceType.rss, url="https://example.com/rss")
        assert src.name == "Test RSS"
        assert src.source_type == SourceType.rss
        assert src.priority == SourcePriority.medium
        assert src.enabled is True

    def test_source_roundtrip(self):
        src = Source(
            name="Test",
            source_type=SourceType.rss,
            url="https://example.com",
            priority=SourcePriority.high,
            tags=["python", "rust"],
        )
        fm = src.to_frontmatter()
        restored = Source.from_frontmatter(fm)
        assert restored.name == src.name
        assert restored.source_type == src.source_type
        assert restored.priority == src.priority
        assert restored.tags == src.tags
        assert restored.id == src.id
        assert restored.created_at == src.created_at

    def test_source_default_id(self):
        src = Source(name="Test", source_type=SourceType.webpage, url="https://example.com")
        assert src.id.startswith("src_")

    def test_source_with_config(self):
        src = Source(
            name="Blog",
            source_type=SourceType.link_scraper,
            url="https://example.com/blog",
            config={"url_pattern": "/blog/.+", "max_items": 5},
        )
        assert src.config["url_pattern"] == "/blog/.+"
        assert src.config["max_items"] == 5

    def test_source_config_roundtrip(self):
        src = Source(
            name="Blog",
            source_type=SourceType.link_scraper,
            url="https://example.com/blog",
            config={"url_pattern": "/blog/.+", "full_content": False},
        )
        fm = src.to_frontmatter()
        restored = Source.from_frontmatter(fm)
        assert restored.config == src.config
        assert restored.source_type == SourceType.link_scraper

    def test_source_config_defaults_to_empty_dict(self):
        src = Source(name="No Config", source_type=SourceType.rss, url="https://example.com/rss")
        assert src.config == {}

    def test_source_link_scraper_type(self):
        src = Source(name="LS", source_type=SourceType.link_scraper, url="https://example.com")
        assert src.source_type == SourceType.link_scraper
        assert src.source_type.value == "link_scraper"


class TestSeed:
    def test_create_seed(self):
        seed = Seed(title="My Article", content="Full markdown content")
        assert seed.title == "My Article"
        assert seed.content == "Full markdown content"
        assert seed.status == SeedStatus.pending
        assert seed.tags == []
        assert seed.source_name == ""

    def test_seed_roundtrip(self):
        seed = Seed(
            title="Test Article",
            content="Article body in **markdown**",
            source_id="src_123",
            source_url="https://example.com",
            source_name="Test Source",
            tags=["ai", "ml"],
            status=SeedStatus.used,
        )
        fm = seed.to_frontmatter()
        restored = Seed.from_frontmatter(fm)
        assert restored.title == seed.title
        assert restored.source_id == seed.source_id
        assert restored.source_url == seed.source_url
        assert restored.source_name == seed.source_name
        assert restored.tags == seed.tags
        assert restored.status == seed.status

    def test_seed_default_status(self):
        seed = Seed(title="New", content="Content")
        assert seed.status == SeedStatus.pending

    def test_seed_approved_status(self):
        seed = Seed(title="Approved", content="Content", status=SeedStatus.approved)
        assert seed.status == SeedStatus.approved

    def test_seed_content_preserved_in_roundtrip(self):
        content = "# Title\n\nThis is the **full** article.\n\n- Point 1\n- Point 2"
        seed = Seed(title="MD Content", content=content)
        fm = seed.to_frontmatter()
        restored = Seed.from_frontmatter(fm)
        assert restored.content == ""


class TestIdea:
    def test_create_idea(self):
        idea = Idea(seed_id="seed_123", title="My Idea", summary="A great idea")
        assert idea.seed_id == "seed_123"
        assert idea.title == "My Idea"
        assert idea.summary == "A great idea"
        assert idea.status == IdeaStatus.pending

    def test_idea_roundtrip(self):
        idea = Idea(
            seed_id="seed_123",
            title="Test Idea",
            summary="Summary here",
            source_url="https://example.com",
            status=IdeaStatus.used,
        )
        fm = idea.to_frontmatter()
        restored = Idea.from_frontmatter(fm)
        assert restored.seed_id == idea.seed_id
        assert restored.title == idea.title
        assert restored.summary == idea.summary
        assert restored.source_url == idea.source_url
        assert restored.status == idea.status

    def test_idea_default_status(self):
        idea = Idea(seed_id="s1", title="New", summary="New idea")
        assert idea.status == IdeaStatus.pending

    def test_idea_default_id(self):
        idea = Idea(seed_id="s1", title="New", summary="New")
        assert idea.id.startswith("idea_")


class TestDraft:
    def test_create_draft(self):
        draft = Draft(idea_id="idea_123", platform="twitter", content="Hello world")
        assert draft.idea_id == "idea_123"
        assert draft.platform == "twitter"
        assert draft.content == "Hello world"
        assert draft.status == DraftStatus.draft

    def test_draft_roundtrip(self):
        draft = Draft(
            idea_id="idea_123",
            platform="linkedin",
            content="Post content here",
            status=DraftStatus.approved,
            notes="Good post",
        )
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.idea_id == draft.idea_id
        assert restored.platform == draft.platform
        assert restored.content == draft.content
        assert restored.status == draft.status
        assert restored.notes == draft.notes

    def test_draft_publish_flow(self):
        draft = Draft(idea_id="idea_1", platform="twitter", content="Content")
        assert draft.status == DraftStatus.draft
        assert draft.published_at is None

        draft.status = DraftStatus.approved
        assert draft.status == DraftStatus.approved

        draft.status = DraftStatus.published
        draft.published_at = datetime.now(timezone.utc)
        assert draft.status == DraftStatus.published
        assert draft.published_at is not None

    def test_draft_media_urls_default(self):
        draft = Draft(idea_id="i1", platform="twitter", content="Hello")
        assert draft.media_urls == []
        assert draft.media_paths == []

    def test_draft_media_urls_roundtrip(self):
        draft = Draft(
            idea_id="i1",
            platform="twitter",
            content="Hello",
            media_urls=["https://example.com/img1.jpg", "https://example.com/img2.png"],
        )
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.media_urls == draft.media_urls
        assert restored.media_paths == []

    def test_draft_media_urls_empty_after_roundtrip(self):
        draft = Draft(idea_id="i1", platform="twitter", content="No media")
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.media_urls == []

    def test_draft_media_paths_roundtrip(self):
        draft = Draft(
            idea_id="i1", platform="twitter", content="Local",
            media_paths=["/tmp/img1.jpg", "/tmp/img2.png"],
        )
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.media_paths == ["/tmp/img1.jpg", "/tmp/img2.png"]

    def test_draft_scheduled_at_default_none(self):
        draft = Draft(idea_id="i1", platform="twitter", content="Hello")
        assert draft.scheduled_at is None

    def test_draft_scheduled_at_roundtrip(self):
        when = datetime(2026, 6, 20, 15, 30, tzinfo=timezone.utc)
        draft = Draft(
            idea_id="i1", platform="twitter", content="Scheduled",
            scheduled_at=when,
        )
        fm = draft.to_frontmatter()
        assert fm["scheduled_at"] == when.isoformat()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.scheduled_at == when

    def test_draft_scheduled_at_omitted_when_none(self):
        draft = Draft(idea_id="i1", platform="twitter", content="No schedule")
        fm = draft.to_frontmatter()
        assert "scheduled_at" not in fm

    def test_draft_scheduled_at_none_after_roundtrip(self):
        draft = Draft(idea_id="i1", platform="twitter", content="No schedule")
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.scheduled_at is None
