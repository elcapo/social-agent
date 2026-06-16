from pathlib import Path

import pytest

from social_agent.models.draft import Draft
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourceType
from social_agent.storage.markdown_store import MarkdownStore


@pytest.fixture
def tmp_store(tmp_path: Path) -> MarkdownStore[Seed]:
    return MarkdownStore[Seed](tmp_path / "seeds", Seed)


@pytest.fixture
def sample_seed() -> Seed:
    return Seed(title="Test Idea", summary="A test seed idea", tags=["test"])


class TestMarkdownStore:
    def test_save_and_get(self, tmp_store: MarkdownStore[Seed], sample_seed: Seed):
        path = tmp_store.save(sample_seed)
        assert path.exists()
        assert path.suffix == ".md"

        retrieved = tmp_store.get(sample_seed.id)
        assert retrieved is not None
        assert retrieved.id == sample_seed.id
        assert retrieved.title == sample_seed.title
        assert retrieved.summary == sample_seed.summary

    def test_get_nonexistent(self, tmp_store: MarkdownStore[Seed]):
        assert tmp_store.get("nonexistent") is None

    def test_list_empty(self, tmp_store: MarkdownStore[Seed]):
        assert tmp_store.list() == []

    def test_list_with_items(self, tmp_store: MarkdownStore[Seed]):
        seeds = [
            Seed(title="Idea 1", summary="Summary 1"),
            Seed(title="Idea 2", summary="Summary 2"),
        ]
        for s in seeds:
            tmp_store.save(s)

        items = tmp_store.list()
        assert len(items) == 2
        assert {i.title for i in items} == {"Idea 1", "Idea 2"}

    def test_list_with_filter(self, tmp_store: MarkdownStore[Seed]):
        s1 = Seed(title="Active", summary="Active seed")
        s2 = Seed(title="Discarded", summary="Discarded seed", status=SeedStatus.discarded)
        tmp_store.save(s1)
        tmp_store.save(s2)

        active = tmp_store.list(filter_fn=lambda s: s.status == SeedStatus.pending)
        assert len(active) == 1
        assert active[0].title == "Active"

    def test_delete(self, tmp_store: MarkdownStore[Seed], sample_seed: Seed):
        tmp_store.save(sample_seed)
        assert tmp_store.count() == 1

        assert tmp_store.delete(sample_seed.id) is True
        assert tmp_store.count() == 0

    def test_delete_nonexistent(self, tmp_store: MarkdownStore[Seed]):
        assert tmp_store.delete("nonexistent") is False

    def test_count(self, tmp_store: MarkdownStore[Seed]):
        assert tmp_store.count() == 0
        tmp_store.save(Seed(title="A", summary="A"))
        assert tmp_store.count() == 1
        tmp_store.save(Seed(title="B", summary="B"))
        assert tmp_store.count() == 2

    def test_preserves_content(self):
        store = MarkdownStore[Draft](Path("data/drafts"), Draft)
        draft = Draft(seed_id="s1", platform="twitter", content="Hello **world**!")
        store.save(draft)
        try:
            retrieved = store.get(draft.id)
            assert retrieved is not None
            assert retrieved.content == "Hello **world**!"
            assert retrieved.platform == "twitter"
        finally:
            store.delete(draft.id)

    def test_back_and_forth_preserves_all_fields(self, tmp_store: MarkdownStore[Seed]):
        original = Seed(
            title="Full Test",
            summary="Full roundtrip test",
            source_id="src_99",
            source_url="https://example.com",
            tags=["a", "b", "c"],
            status=SeedStatus.used,
        )
        tmp_store.save(original)
        retrieved = tmp_store.get(original.id)
        assert retrieved is not None
        assert retrieved.title == original.title
        assert retrieved.summary == original.summary
        assert retrieved.source_id == original.source_id
        assert retrieved.source_url == original.source_url
        assert retrieved.tags == original.tags
        assert retrieved.status == original.status
        assert retrieved.created_at == original.created_at
