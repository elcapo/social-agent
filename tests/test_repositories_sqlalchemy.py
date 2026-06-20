"""Unit tests for the SQLAlchemy 2.0 sync repository implementations.

Uses an in-memory SQLite engine per test class (shared via a sessionmaker) so
FK constraints and the JSON columns work as in production. Covers:
- CRUD operations (save/get/list/delete/count) for all four entities.
- Entity-specific queries (`list_active`, `find_by_type`, `list_by_status`,
  `list_by_source`, `list_by_platform`, `list_scheduled`).
- Round-trip Pydantic <-> ORM mapping (lists/JSON fields, datetimes, enums).
- Protocol conformance (structural typing via `isinstance`).
- The factory selecting the right backend from `settings.storage_backend`.
- `MarkdownStore` wrappers satisfying the Protocols (duck typing).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourcePriority, SourceType
from social_agent.storage import (
    factory,
    get_draft_repository,
    get_idea_repository,
    get_seed_repository,
    get_source_repository,
)
from social_agent.storage.db import Base
from social_agent.storage.markdown_repositories import (
    MarkdownDraftRepository,
    MarkdownIdeaRepository,
    MarkdownSeedRepository,
    MarkdownSourceRepository,
)
from social_agent.storage.repositories import (
    DraftRepository,
    IdeaRepository,
    Repository,
    SeedRepository,
    SourceRepository,
)
from social_agent.storage.sqlalchemy_repositories import (
    SqlAlchemyDraftRepository,
    SqlAlchemyIdeaRepository,
    SqlAlchemySeedRepository,
    SqlAlchemySourceRepository,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def session_factory():
    """Yield a `sessionmaker` bound to a fresh in-memory SQLite DB."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    engine.dispose()


@pytest.fixture
def src_repo(session_factory):
    return SqlAlchemySourceRepository(session_factory)


@pytest.fixture
def seed_repo(session_factory):
    return SqlAlchemySeedRepository(session_factory)


@pytest.fixture
def idea_repo(session_factory):
    return SqlAlchemyIdeaRepository(session_factory)


@pytest.fixture
def draft_repo(session_factory):
    return SqlAlchemyDraftRepository(session_factory)


@pytest.fixture
def sample_source() -> Source:
    return Source(
        name="Hacker News",
        source_type=SourceType.rss,
        url="https://news.ycombinator.com/rss",
        priority=SourcePriority.high,
        tags=["tech", "news"],
        config={"max_items": 10},
    )


@pytest.fixture
def sample_seed() -> Seed:
    return Seed(
        title="Test Article",
        content="Full **markdown** body",
        source_name="Hacker News",
        tags=["test"],
        status=SeedStatus.pending,
    )


@pytest.fixture
def sample_idea() -> Idea:
    return Idea(
        seed_id="seed_abc",
        title="Idea title",
        summary="A short summary.",
        source_url="https://example.com/article",
        status=IdeaStatus.pending,
    )


@pytest.fixture
def sample_draft() -> Draft:
    return Draft(
        idea_id="idea_abc",
        platform="twitter",
        content="Hello world!",
        status=DraftStatus.draft,
        media_urls=["https://img.example.com/a.png"],
        media_paths=["/tmp/a.png"],
    )


# ── Protocol conformance ────────────────────────────────────────────────────


class TestProtocolConformance:
    def test_source_repo_satisfies_repository(self, src_repo):
        assert isinstance(src_repo, Repository)
        assert isinstance(src_repo, SourceRepository)

    def test_seed_repo_satisfies_repository(self, seed_repo):
        assert isinstance(seed_repo, Repository)
        assert isinstance(seed_repo, SeedRepository)

    def test_idea_repo_satisfies_repository(self, idea_repo):
        assert isinstance(idea_repo, Repository)
        assert isinstance(idea_repo, IdeaRepository)

    def test_draft_repo_satisfies_repository(self, draft_repo):
        assert isinstance(draft_repo, Repository)
        assert isinstance(draft_repo, DraftRepository)


# ── Source repository ───────────────────────────────────────────────────────


class TestSqlAlchemySourceRepository:
    def test_save_and_get(self, src_repo, sample_source):
        src_repo.save(sample_source)
        got = src_repo.get(sample_source.id)
        assert got is not None
        assert got.name == sample_source.name
        assert got.source_type == SourceType.rss
        assert got.priority == SourcePriority.high
        assert got.tags == ["tech", "news"]
        assert got.config == {"max_items": 10}
        assert got.enabled is True

    def test_get_nonexistent(self, src_repo):
        assert src_repo.get("src_nope") is None

    def test_get_by_id_alias(self, src_repo, sample_source):
        src_repo.save(sample_source)
        assert src_repo.get_by_id(sample_source.id) is not None

    def test_list_empty(self, src_repo):
        assert src_repo.list() == []
        assert src_repo.count() == 0

    def test_list_with_items(self, src_repo):
        s1 = Source(name="A", source_type=SourceType.rss, url="http://a")
        s2 = Source(name="B", source_type=SourceType.webpage, url="http://b")
        src_repo.save(s1)
        src_repo.save(s2)
        items = src_repo.list()
        assert len(items) == 2
        assert {i.name for i in items} == {"A", "B"}
        assert src_repo.count() == 2

    def test_list_with_filter(self, src_repo):
        src_repo.save(Source(name="A", source_type=SourceType.rss, url="http://a"))
        src_repo.save(Source(name="B", source_type=SourceType.webpage, url="http://b"))
        only_rss = src_repo.list(filter_fn=lambda s: s.source_type == SourceType.rss)
        assert len(only_rss) == 1
        assert only_rss[0].name == "A"

    def test_save_updates_existing(self, src_repo, sample_source):
        src_repo.save(sample_source)
        sample_source.enabled = False
        sample_source.name = "Renamed"
        src_repo.save(sample_source)
        got = src_repo.get(sample_source.id)
        assert got.enabled is False
        assert got.name == "Renamed"
        assert src_repo.count() == 1  # no duplicate

    def test_delete(self, src_repo, sample_source):
        src_repo.save(sample_source)
        assert src_repo.delete(sample_source.id) is True
        assert src_repo.get(sample_source.id) is None
        assert src_repo.count() == 0

    def test_delete_nonexistent(self, src_repo):
        assert src_repo.delete("nope") is False

    def test_list_active(self, src_repo):
        src_repo.save(Source(name="on", source_type=SourceType.rss, url="u", enabled=True))
        src_repo.save(Source(name="off", source_type=SourceType.rss, url="u2", enabled=False))
        active = src_repo.list_active()
        assert len(active) == 1
        assert active[0].name == "on"

    def test_find_by_type(self, src_repo):
        src_repo.save(Source(name="r", source_type=SourceType.rss, url="u"))
        src_repo.save(Source(name="w", source_type=SourceType.webpage, url="u2"))
        src_repo.save(Source(name="r2", source_type=SourceType.rss, url="u3"))
        rss = src_repo.find_by_type(SourceType.rss)
        assert len(rss) == 2
        assert {s.name for s in rss} == {"r", "r2"}

    def test_last_fetched_roundtrip(self, src_repo, sample_source):
        when = datetime.now(timezone.utc)
        sample_source.last_fetched = when
        src_repo.save(sample_source)
        got = src_repo.get(sample_source.id)
        assert got.last_fetched is not None
        # Compare at microsecond resolution (SQLite stores ISO strings).
        assert got.last_fetched.replace(microsecond=0) == when.replace(microsecond=0)


# ── Seed repository ─────────────────────────────────────────────────────────


class TestSqlAlchemySeedRepository:
    def test_save_and_get(self, seed_repo, sample_seed):
        seed_repo.save(sample_seed)
        got = seed_repo.get(sample_seed.id)
        assert got is not None
        assert got.title == sample_seed.title
        assert got.content == sample_seed.content
        assert got.tags == ["test"]
        assert got.status == SeedStatus.pending

    def test_list_by_status(self, seed_repo):
        seed_repo.save(Seed(title="p", content="c", status=SeedStatus.pending))
        seed_repo.save(Seed(title="a", content="c", status=SeedStatus.approved))
        seed_repo.save(Seed(title="p2", content="c", status=SeedStatus.pending))
        pending = seed_repo.list_by_status(SeedStatus.pending)
        assert len(pending) == 2
        assert {s.title for s in pending} == {"p", "p2"}

    def test_list_by_source(self, seed_repo):
        seed_repo.save(Seed(title="1", content="c", source_id="src_A"))
        seed_repo.save(Seed(title="2", content="c", source_id="src_B"))
        seed_repo.save(Seed(title="3", content="c", source_id="src_A"))
        of_a = seed_repo.list_by_source("src_A")
        assert len(of_a) == 2
        assert {s.title for s in of_a} == {"1", "3"}

    def test_delete(self, seed_repo, sample_seed):
        seed_repo.save(sample_seed)
        assert seed_repo.delete(sample_seed.id) is True
        assert seed_repo.get(sample_seed.id) is None

    def test_count(self, seed_repo):
        assert seed_repo.count() == 0
        seed_repo.save(Seed(title="x", content="c"))
        assert seed_repo.count() == 1


# ── Idea repository ─────────────────────────────────────────────────────────


class TestSqlAlchemyIdeaRepository:
    def test_save_and_get(self, idea_repo, sample_idea):
        idea_repo.save(sample_idea)
        got = idea_repo.get(sample_idea.id)
        assert got is not None
        assert got.title == sample_idea.title
        assert got.summary == sample_idea.summary
        assert got.status == IdeaStatus.pending
        assert got.seed_id == "seed_abc"

    def test_list_by_status(self, idea_repo):
        idea_repo.save(Idea(seed_id="s1", title="t1", summary="x", status=IdeaStatus.pending))
        idea_repo.save(Idea(seed_id="s2", title="t2", summary="x", status=IdeaStatus.used))
        idea_repo.save(Idea(seed_id="s3", title="t3", summary="x", status=IdeaStatus.pending))
        pending = idea_repo.list_by_status(IdeaStatus.pending)
        assert len(pending) == 2
        assert {i.title for i in pending} == {"t1", "t3"}

    def test_update_status(self, idea_repo, sample_idea):
        idea_repo.save(sample_idea)
        sample_idea.status = IdeaStatus.used
        idea_repo.save(sample_idea)
        assert idea_repo.get(sample_idea.id).status == IdeaStatus.used
        assert idea_repo.count() == 1

    def test_delete(self, idea_repo, sample_idea):
        idea_repo.save(sample_idea)
        assert idea_repo.delete(sample_idea.id) is True
        assert idea_repo.get(sample_idea.id) is None


# ── Draft repository ────────────────────────────────────────────────────────


class TestSqlAlchemyDraftRepository:
    def test_save_and_get_roundtrip(self, draft_repo, sample_draft):
        draft_repo.save(sample_draft)
        got = draft_repo.get(sample_draft.id)
        assert got is not None
        assert got.platform == "twitter"
        assert got.content == "Hello world!"
        assert got.status == DraftStatus.draft
        assert got.media_urls == ["https://img.example.com/a.png"]
        assert got.media_paths == ["/tmp/a.png"]
        assert got.publish_attempts == 0

    def test_list_by_platform(self, draft_repo):
        draft_repo.save(Draft(idea_id="i1", platform="twitter", content="x"))
        draft_repo.save(Draft(idea_id="i2", platform="linkedin", content="y"))
        draft_repo.save(Draft(idea_id="i3", platform="twitter", content="z"))
        tw = draft_repo.list_by_platform("twitter")
        assert len(tw) == 2

    def test_list_by_status(self, draft_repo):
        draft_repo.save(Draft(idea_id="i1", platform="twitter", status=DraftStatus.draft))
        draft_repo.save(Draft(idea_id="i2", platform="twitter", status=DraftStatus.approved))
        draft_repo.save(Draft(idea_id="i3", platform="twitter", status=DraftStatus.draft))
        drafts = draft_repo.list_by_status(DraftStatus.draft)
        assert len(drafts) == 2

    def test_update_preserves_media_lists(self, draft_repo, sample_draft):
        draft_repo.save(sample_draft)
        sample_draft.media_urls.append("https://img.example.com/b.jpg")
        sample_draft.publish_attempts = 3
        draft_repo.save(sample_draft)
        got = draft_repo.get(sample_draft.id)
        assert got.media_urls == [
            "https://img.example.com/a.png",
            "https://img.example.com/b.jpg",
        ]
        assert got.publish_attempts == 3

    def test_list_scheduled_empty_when_none_scheduled(self, draft_repo):
        draft_repo.save(Draft(idea_id="i", platform="twitter"))
        assert draft_repo.list_scheduled() == []

    def test_list_scheduled_skips_future(self, draft_repo):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        d = Draft(idea_id="i", platform="twitter", status=DraftStatus.draft, scheduled_at=future)
        draft_repo.save(d)
        assert draft_repo.list_scheduled() == []

    def test_list_scheduled_includes_past(self, draft_repo):
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        d = Draft(idea_id="i", platform="twitter", status=DraftStatus.draft, scheduled_at=past)
        draft_repo.save(d)
        due = draft_repo.list_scheduled()
        assert len(due) == 1
        assert due[0].id == d.id

    def test_list_scheduled_filters_by_status(self, draft_repo):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        d1 = Draft(idea_id="i1", platform="twitter", status=DraftStatus.draft, scheduled_at=past)
        d2 = Draft(
            idea_id="i2", platform="twitter", status=DraftStatus.published, scheduled_at=past
        )
        draft_repo.save(d1)
        draft_repo.save(d2)
        due = draft_repo.list_scheduled(status_values=("draft", "approved"))
        assert {x.id for x in due} == {d1.id}

    def test_list_scheduled_includes_approved(self, draft_repo):
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        d = Draft(idea_id="i", platform="twitter", status=DraftStatus.approved, scheduled_at=past)
        draft_repo.save(d)
        due = draft_repo.list_scheduled(status_values=("draft", "approved"))
        assert len(due) == 1

    def test_list_scheduled_naive_datetime_treated_as_utc(self, draft_repo):
        past_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        d = Draft(
            idea_id="i", platform="twitter", status=DraftStatus.draft, scheduled_at=past_naive
        )
        draft_repo.save(d)
        due = draft_repo.list_scheduled()
        assert len(due) == 1

    def test_list_scheduled_explicit_since(self, draft_repo):
        now = datetime.now(timezone.utc)
        d = Draft(
            idea_id="i",
            platform="twitter",
            status=DraftStatus.draft,
            scheduled_at=now + timedelta(days=1),
        )
        draft_repo.save(d)
        # With `since` in the future, the draft is due.
        due = draft_repo.list_scheduled(since=now + timedelta(days=2))
        assert len(due) == 1
        # With `since` in the past, the draft is not due yet.
        assert draft_repo.list_scheduled(since=now) == []

    def test_delete(self, draft_repo, sample_draft):
        draft_repo.save(sample_draft)
        assert draft_repo.delete(sample_draft.id) is True
        assert draft_repo.get(sample_draft.id) is None

    def test_published_at_roundtrip(self, draft_repo):
        when = datetime.now(timezone.utc)
        d = Draft(
            idea_id="i",
            platform="twitter",
            status=DraftStatus.published,
            published_at=when,
            platform_post_id="123",
        )
        draft_repo.save(d)
        got = draft_repo.get(d.id)
        assert got.published_at is not None
        assert got.published_at.replace(microsecond=0) == when.replace(microsecond=0)
        assert got.platform_post_id == "123"


# ── Markdown wrappers satisfy Protocols ─────────────────────────────────────


class TestMarkdownRepositoryWrappers:
    @pytest.fixture
    def base_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    def test_all_satisfy_protocols(self, base_dir):
        src = MarkdownSourceRepository(base_dir / "src", Source)
        seed = MarkdownSeedRepository(base_dir / "seeds", Seed)
        idea = MarkdownIdeaRepository(base_dir / "ideas", Idea)
        draft = MarkdownDraftRepository(base_dir / "drafts", Draft)
        assert isinstance(src, SourceRepository)
        assert isinstance(seed, SeedRepository)
        assert isinstance(idea, IdeaRepository)
        assert isinstance(draft, DraftRepository)

    def test_source_wrapper_list_active_and_find_by_type(self, base_dir):
        repo = MarkdownSourceRepository(base_dir / "src", Source)
        repo.save(Source(name="on", source_type=SourceType.rss, url="u", enabled=True))
        repo.save(Source(name="off", source_type=SourceType.webpage, url="u2", enabled=False))
        assert len(repo.list_active()) == 1
        assert repo.list_active()[0].name == "on"
        assert len(repo.find_by_type(SourceType.rss)) == 1
        assert len(repo.find_by_type(SourceType.webpage)) == 1

    def test_seed_wrapper_queries(self, base_dir):
        repo = MarkdownSeedRepository(base_dir / "seeds", Seed)
        repo.save(Seed(title="p", content="c", source_id="src_A", status=SeedStatus.pending))
        repo.save(Seed(title="a", content="c", source_id="src_B", status=SeedStatus.approved))
        assert len(repo.list_by_status(SeedStatus.pending)) == 1
        assert len(repo.list_by_source("src_A")) == 1

    def test_idea_wrapper_queries(self, base_dir):
        repo = MarkdownIdeaRepository(base_dir / "ideas", Idea)
        repo.save(Idea(seed_id="s1", title="t", summary="x", status=IdeaStatus.pending))
        repo.save(Idea(seed_id="s2", title="t2", summary="x", status=IdeaStatus.used))
        assert len(repo.list_by_status(IdeaStatus.pending)) == 1

    def test_draft_wrapper_list_scheduled_matches_markdown_store(self, base_dir):
        repo = MarkdownDraftRepository(base_dir / "drafts", Draft)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        repo.save(
            Draft(idea_id="i", platform="twitter", status=DraftStatus.draft, scheduled_at=past)
        )
        repo.save(
            Draft(idea_id="i", platform="twitter", status=DraftStatus.draft, scheduled_at=future)
        )
        due = repo.list_scheduled()
        assert len(due) == 1


# ── Factory ─────────────────────────────────────────────────────────────────


class TestFactory:
    def test_markdown_backend_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "data_dir", tmp_path)
        monkeypatch.setattr(settings, "storage_backend", "markdown")
        monkeypatch.setattr(settings, "sqlite_path", None)
        factory.reset_factory_cache()
        assert isinstance(get_source_repository(), MarkdownSourceRepository)
        assert isinstance(get_seed_repository(), MarkdownSeedRepository)
        assert isinstance(get_idea_repository(), MarkdownIdeaRepository)
        assert isinstance(get_draft_repository(), MarkdownDraftRepository)

    def test_sqlite_backend(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "data_dir", tmp_path)
        monkeypatch.setattr(settings, "storage_backend", "sqlite")
        monkeypatch.setattr(settings, "sqlite_path", tmp_path / "test.db")
        factory.reset_factory_cache()
        # Reset the cached engine so it picks up the new sqlite_path.
        from social_agent.storage import db as dbmod

        dbmod.reset_engine()
        try:
            assert isinstance(get_source_repository(), SqlAlchemySourceRepository)
            assert isinstance(get_seed_repository(), SqlAlchemySeedRepository)
            assert isinstance(get_idea_repository(), SqlAlchemyIdeaRepository)
            assert isinstance(get_draft_repository(), SqlAlchemyDraftRepository)
        finally:
            dbmod.reset_engine()
            factory.reset_factory_cache()

    def test_sqlite_backend_creates_tables(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "data_dir", tmp_path)
        monkeypatch.setattr(settings, "storage_backend", "sqlite")
        monkeypatch.setattr(settings, "sqlite_path", tmp_path / "fresh.db")
        factory.reset_factory_cache()
        from social_agent.storage import db as dbmod

        dbmod.reset_engine()
        try:
            repo = get_source_repository()
            s = Source(name="x", source_type=SourceType.rss, url="http://x")
            repo.save(s)
            assert repo.get(s.id) is not None
        finally:
            dbmod.reset_engine()
            factory.reset_factory_cache()

    def test_invalid_backend_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "storage_backend", "postgres")
        factory.reset_factory_cache()
        with pytest.raises(ValueError, match="Unknown storage backend"):
            get_source_repository()

    def test_explicit_backend_overrides_settings(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "data_dir", tmp_path)
        monkeypatch.setattr(settings, "storage_backend", "sqlite")
        factory.reset_factory_cache()
        # Explicit markdown should win over settings.sqlite.
        assert isinstance(get_source_repository(backend="markdown"), MarkdownSourceRepository)


# ── Cross-backend parity smoke test ─────────────────────────────────────────


class TestCrossBackendParity:
    """The same sequence of operations should produce equivalent state on
    both backends. This guards against drift between the Markdown and SQLite
    implementations of the Protocols.
    """

    def _populate(self, repo):
        s = Source(
            name=" parity",
            source_type=SourceType.rss,
            url="http://parity",
            priority=SourcePriority.medium,
            tags=["a", "b"],
        )
        repo.save(s)
        s.enabled = False
        repo.save(s)
        return s

    def test_markdown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "data_dir", tmp_path)
        repo = MarkdownSourceRepository(tmp_path / "src", Source)
        s = self._populate(repo)
        assert repo.get(s.id).enabled is False
        assert len(repo.list_active()) == 0
        assert len(repo.find_by_type(SourceType.rss)) == 1
        assert repo.delete(s.id) is True
        assert repo.get(s.id) is None

    def test_sqlite(self, session_factory):
        repo = SqlAlchemySourceRepository(session_factory)
        s = self._populate(repo)
        assert repo.get(s.id).enabled is False
        assert len(repo.list_active()) == 0
        assert len(repo.find_by_type(SourceType.rss)) == 1
        assert repo.delete(s.id) is True
        assert repo.get(s.id) is None
