from social_agent.collectors.base import BaseCollector, CollectedItem


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
