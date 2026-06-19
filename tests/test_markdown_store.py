from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea
from social_agent.models.seed import Seed, SeedStatus
from social_agent.storage.markdown_store import MarkdownStore


@pytest.fixture
def tmp_seed_store(tmp_path: Path) -> MarkdownStore[Seed]:
    return MarkdownStore[Seed](tmp_path / "seeds", Seed)


@pytest.fixture
def tmp_idea_store(tmp_path: Path) -> MarkdownStore[Idea]:
    return MarkdownStore[Idea](tmp_path / "ideas", Idea)


@pytest.fixture
def sample_seed() -> Seed:
    return Seed(title="Test Article", content="Full **markdown** body", tags=["test"])


class TestMarkdownStoreSeed:
    def test_save_and_get(self, tmp_seed_store: MarkdownStore[Seed], sample_seed: Seed):
        path = tmp_seed_store.save(sample_seed)
        assert path.exists()
        assert path.suffix == ".md"

        retrieved = tmp_seed_store.get(sample_seed.id)
        assert retrieved is not None
        assert retrieved.id == sample_seed.id
        assert retrieved.title == sample_seed.title
        assert retrieved.content == sample_seed.content

    def test_get_nonexistent(self, tmp_seed_store: MarkdownStore[Seed]):
        assert tmp_seed_store.get("nonexistent") is None

    def test_list_empty(self, tmp_seed_store: MarkdownStore[Seed]):
        assert tmp_seed_store.list() == []

    def test_list_with_items(self, tmp_seed_store: MarkdownStore[Seed]):
        seeds = [
            Seed(title="Article 1", content="Body 1"),
            Seed(title="Article 2", content="Body 2"),
        ]
        for s in seeds:
            tmp_seed_store.save(s)

        items = tmp_seed_store.list()
        assert len(items) == 2
        assert {i.title for i in items} == {"Article 1", "Article 2"}

    def test_list_with_filter(self, tmp_seed_store: MarkdownStore[Seed]):
        s1 = Seed(title="Active", content="Body")
        s2 = Seed(title="Discarded", content="Body", status=SeedStatus.discarded)
        tmp_seed_store.save(s1)
        tmp_seed_store.save(s2)

        active = tmp_seed_store.list(filter_fn=lambda s: s.status == SeedStatus.pending)
        assert len(active) == 1
        assert active[0].title == "Active"

    def test_delete(self, tmp_seed_store: MarkdownStore[Seed], sample_seed: Seed):
        tmp_seed_store.save(sample_seed)
        assert tmp_seed_store.count() == 1

        assert tmp_seed_store.delete(sample_seed.id) is True
        assert tmp_seed_store.count() == 0

    def test_delete_nonexistent(self, tmp_seed_store: MarkdownStore[Seed]):
        assert tmp_seed_store.delete("nonexistent") is False

    def test_count(self, tmp_seed_store: MarkdownStore[Seed]):
        assert tmp_seed_store.count() == 0
        tmp_seed_store.save(Seed(title="A", content="A"))
        assert tmp_seed_store.count() == 1
        tmp_seed_store.save(Seed(title="B", content="B"))
        assert tmp_seed_store.count() == 2

    def test_back_and_forth_preserves_all_fields(self, tmp_seed_store: MarkdownStore[Seed]):
        original = Seed(
            title="Full Test",
            content="Markdown **body** content",
            source_id="src_99",
            source_url="https://example.com",
            source_name="Source Name",
            tags=["tag1", "tag2"],
            status=SeedStatus.approved,
        )
        tmp_seed_store.save(original)
        retrieved = tmp_seed_store.get(original.id)
        assert retrieved is not None
        assert retrieved.title == original.title
        assert retrieved.content == original.content
        assert retrieved.source_id == original.source_id
        assert retrieved.source_url == original.source_url
        assert retrieved.source_name == original.source_name
        assert retrieved.tags == original.tags
        assert retrieved.status == original.status
        assert retrieved.created_at == original.created_at

    def test_preserves_markdown_content(self):
        store = MarkdownStore[Seed](Path("data/seeds"), Seed)
        seed = Seed(title="MD Test", content="Hello **world**!\n\n- Item 1\n- Item 2")
        store.save(seed)
        try:
            retrieved = store.get(seed.id)
            assert retrieved is not None
            assert retrieved.content == "Hello **world**!\n\n- Item 1\n- Item 2"
        finally:
            store.delete(seed.id)


class TestMarkdownStoreIdea:
    def test_save_and_get(self, tmp_idea_store: MarkdownStore[Idea]):
        idea = Idea(seed_id="seed_1", title="Test Idea", summary="Summary here")
        path = tmp_idea_store.save(idea)
        assert path.exists()

        retrieved = tmp_idea_store.get(idea.id)
        assert retrieved is not None
        assert retrieved.id == idea.id
        assert retrieved.seed_id == "seed_1"
        assert retrieved.title == "Test Idea"
        assert retrieved.summary == "Summary here"

    def test_get_nonexistent(self, tmp_idea_store: MarkdownStore[Idea]):
        assert tmp_idea_store.get("nonexistent") is None

    def test_list_with_filter(self, tmp_idea_store: MarkdownStore[Idea]):
        i1 = Idea(seed_id="s1", title="Pending", summary="P")
        i2 = Idea(seed_id="s2", title="Used", summary="U", status=SeedStatus.used)
        tmp_idea_store.save(i1)
        tmp_idea_store.save(i2)

        pending = tmp_idea_store.list(filter_fn=lambda i: i.status.value == "pending")
        assert len(pending) == 1
        assert pending[0].title == "Pending"

    def test_delete(self, tmp_idea_store: MarkdownStore[Idea]):
        idea = Idea(seed_id="s1", title="Test", summary="Test")
        tmp_idea_store.save(idea)
        assert tmp_idea_store.count() == 1
        assert tmp_idea_store.delete(idea.id) is True
        assert tmp_idea_store.count() == 0


class TestMarkdownStoreDraftContent:
    def test_preserves_content(self):
        store = MarkdownStore[Draft](Path("data/drafts"), Draft)
        draft = Draft(idea_id="i1", platform="twitter", content="Hello **world**!")
        store.save(draft)
        try:
            retrieved = store.get(draft.id)
            assert retrieved is not None
            assert retrieved.content == "Hello **world**!"
            assert retrieved.platform == "twitter"
        finally:
            store.delete(draft.id)


class TestMarkdownStoreListScheduled:
    @pytest.fixture
    def tmp_draft_store(self, tmp_path: Path) -> MarkdownStore[Draft]:
        return MarkdownStore[Draft](tmp_path / "drafts", Draft)

    def test_list_scheduled_empty(self, tmp_draft_store):
        assert tmp_draft_store.list_scheduled() == []

    def test_list_scheduled_returns_due_draft(self, tmp_draft_store):
        due = Draft(
            idea_id="i1", platform="twitter", content="due",
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        tmp_draft_store.save(due)
        result = tmp_draft_store.list_scheduled()
        assert len(result) == 1
        assert result[0].id == due.id

    def test_list_scheduled_excludes_future(self, tmp_draft_store):
        future = Draft(
            idea_id="i1", platform="twitter", content="future",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        tmp_draft_store.save(future)
        assert tmp_draft_store.list_scheduled() == []

    def test_list_scheduled_excludes_unscheduled(self, tmp_draft_store):
        plain = Draft(idea_id="i1", platform="twitter", content="plain")
        tmp_draft_store.save(plain)
        assert tmp_draft_store.list_scheduled() == []

    def test_list_scheduled_excludes_non_draft_status(self, tmp_draft_store):
        published = Draft(
            idea_id="i1", platform="twitter", content="done",
            status=DraftStatus.published,
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        tmp_draft_store.save(published)
        assert tmp_draft_store.list_scheduled() == []

    def test_list_scheduled_with_explicit_since(self, tmp_draft_store):
        cutoff = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)
        before = Draft(
            idea_id="i1", platform="twitter", content="before",
            scheduled_at=datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc),
        )
        after = Draft(
            idea_id="i2", platform="twitter", content="after",
            scheduled_at=datetime(2026, 6, 19, 14, 0, tzinfo=timezone.utc),
        )
        tmp_draft_store.save(before)
        tmp_draft_store.save(after)
        result = tmp_draft_store.list_scheduled(since=cutoff)
        assert [d.id for d in result] == [before.id]

    def test_list_scheduled_handles_naive_datetime(self, tmp_draft_store):
        naive_due = Draft(
            idea_id="i1", platform="twitter", content="naive",
            scheduled_at=datetime(2020, 1, 1, 0, 0),
        )
        tmp_draft_store.save(naive_due)
        result = tmp_draft_store.list_scheduled()
        assert len(result) == 1
        assert result[0].id == naive_due.id

    def test_list_scheduled_roundtrips_through_disk(self, tmp_draft_store):
        due = Draft(
            idea_id="i1", platform="twitter", content="persisted",
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        tmp_draft_store.save(due)
        result = tmp_draft_store.list_scheduled()
        assert len(result) == 1
        assert result[0].scheduled_at == due.scheduled_at
