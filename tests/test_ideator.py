from datetime import datetime, timezone
from unittest.mock import patch

from social_agent.agents.ideator import IdeatorAgent
from social_agent.collectors.base import CollectedItem

MOCK_SIMPLE = """[
  {"title": "Idea 1", "summary": "Summary 1", "tags": ["tag1"]},
  {"title": "Idea 2", "summary": "Summary 2", "tags": ["tag2", "tag3"]}
]"""

MOCK_WITH_SOURCE = """[
  {"title": "Idea 1", "summary": "Summary 1", "tags": ["tag1"], "source_index": 1},
  {"title": "Idea 2", "summary": "Summary 2", "tags": ["tag2"], "source_index": 2}
]"""

RUN_PATH = "social_agent.agents.ideator.IdeatorAgent.run"


def _with_side(effect: str):
    return patch(RUN_PATH, return_value=effect)


class TestIdeatorAgent:
    def test_generate_seeds_empty_on_invalid_response(self):
        with _with_side("not valid json"):
            agent = IdeatorAgent()
            seeds = agent.generate_seeds("interests", [])
            assert seeds == []

    def test_generate_seeds_parses_json(self):
        with _with_side(MOCK_SIMPLE):
            agent = IdeatorAgent()
            items = [
                CollectedItem(
                    title="Source Item",
                    content="Content here",
                    url="https://example.com",
                    source_id="src_1",
                    source_name="Test Source",
                    published=datetime.now(timezone.utc),
                )
            ]
            seeds = agent.generate_seeds("Some interests", items)
            assert len(seeds) == 2
            assert seeds[0].title == "Idea 1"
            assert seeds[0].summary == "Summary 1"
            assert seeds[0].tags == ["tag1"]
            assert seeds[0].status.value == "pending"

    def test_generate_seeds_with_real_items(self):
        with _with_side(MOCK_SIMPLE):
            agent = IdeatorAgent()
            items = [
                CollectedItem(
                    title="A", content="B", url="https://e.com",
                    source_id="s1", source_name="S1",
                ),
                CollectedItem(
                    title="C", content="D", url="https://e2.com",
                    source_id="s2", source_name="S2",
                ),
            ]
            seeds = agent.generate_seeds("Tech interests", items)
            assert len(seeds) == 2
            assert all(s.created_at is not None for s in seeds)

    def test_generate_seeds_links_to_source(self):
        with _with_side(MOCK_WITH_SOURCE):
            agent = IdeatorAgent()
            items = [
                CollectedItem(
                    title="Article A", content="Body A",
                    url="https://example.com/a",
                    source_id="src_a", source_name="Source A",
                ),
                CollectedItem(
                    title="Article B", content="Body B",
                    url="https://example.com/b",
                    source_id="src_b", source_name="Source B",
                ),
            ]
            seeds = agent.generate_seeds("Interests", items)
            assert len(seeds) == 2
            assert seeds[0].source_id == "src_a"
            assert seeds[0].source_url == "https://example.com/a"
            assert seeds[1].source_id == "src_b"
            assert seeds[1].source_url == "https://example.com/b"

    def test_generate_seeds_no_source_when_index_missing(self):
        with _with_side(MOCK_SIMPLE):
            agent = IdeatorAgent()
            items = [
                CollectedItem(
                    title="A", content="B", url="https://e.com",
                    source_id="s1", source_name="S1",
                ),
            ]
            seeds = agent.generate_seeds("Interests", items)
            assert len(seeds) == 2
            assert seeds[0].source_id is None
            assert seeds[0].source_url is None
