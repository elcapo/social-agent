from datetime import datetime, timezone

from social_agent.models.draft import Draft, DraftStatus
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


class TestSeed:
    def test_create_seed(self):
        seed = Seed(title="My Idea", summary="A great idea for a post")
        assert seed.title == "My Idea"
        assert seed.summary == "A great idea for a post"
        assert seed.status == SeedStatus.pending

    def test_seed_roundtrip(self):
        seed = Seed(
            title="Test Seed",
            summary="Summary here",
            source_id="src_123",
            source_url="https://example.com",
            tags=["ai", "ml"],
            status=SeedStatus.used,
        )
        fm = seed.to_frontmatter()
        restored = Seed.from_frontmatter(fm)
        assert restored.title == seed.title
        assert restored.summary == seed.summary
        assert restored.source_id == seed.source_id
        assert restored.status == seed.status
        assert restored.tags == seed.tags

    def test_seed_default_status(self):
        seed = Seed(title="New", summary="New idea")
        assert seed.status == SeedStatus.pending


class TestDraft:
    def test_create_draft(self):
        draft = Draft(seed_id="seed_123", platform="twitter", content="Hello world")
        assert draft.seed_id == "seed_123"
        assert draft.platform == "twitter"
        assert draft.content == "Hello world"
        assert draft.status == DraftStatus.draft

    def test_draft_roundtrip(self):
        draft = Draft(
            seed_id="seed_123",
            platform="linkedin",
            content="Post content here",
            status=DraftStatus.approved,
            notes="Good post",
        )
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.seed_id == draft.seed_id
        assert restored.platform == draft.platform
        assert restored.content == draft.content
        assert restored.status == draft.status
        assert restored.notes == draft.notes

    def test_draft_publish_flow(self):
        draft = Draft(seed_id="seed_1", platform="twitter", content="Content")
        assert draft.status == DraftStatus.draft
        assert draft.published_at is None

        draft.status = DraftStatus.approved
        assert draft.status == DraftStatus.approved

        draft.status = DraftStatus.published
        draft.published_at = datetime.now(timezone.utc)
        assert draft.status == DraftStatus.published
        assert draft.published_at is not None

    def test_draft_media_urls_default(self):
        draft = Draft(seed_id="s1", platform="twitter", content="Hello")
        assert draft.media_urls == []
        assert draft.media_paths == []

    def test_draft_media_urls_roundtrip(self):
        draft = Draft(
            seed_id="s1",
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
        draft = Draft(seed_id="s1", platform="twitter", content="No media")
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.media_urls == []

    def test_draft_media_paths_roundtrip(self):
        draft = Draft(
            seed_id="s1", platform="twitter", content="Local",
            media_paths=["/tmp/img1.jpg", "/tmp/img2.png"],
        )
        fm = draft.to_frontmatter()
        fm["content"] = draft.content
        restored = Draft.from_frontmatter(fm)
        assert restored.media_paths == ["/tmp/img1.jpg", "/tmp/img2.png"]
