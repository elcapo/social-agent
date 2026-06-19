from unittest.mock import patch

from social_agent.agents.ideator import IdeatorAgent
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed

MOCK_SIMPLE = """{"title": "Idea Title", "summary": "Idea summary text"}"""

RUN_PATH = "social_agent.agents.ideator.IdeatorAgent.run"


def _with_side(effect: str):
    return patch(RUN_PATH, return_value=effect)


class TestIdeatorAgent:
    def test_generate_idea_returns_none_on_invalid_response(self):
        with _with_side("not valid json"):
            agent = IdeatorAgent()
            seed = Seed(title="Test", content="Article content")
            result = agent.generate_idea(seed, "interests")
            assert result is None

    def test_generate_idea_returns_idea(self):
        with _with_side(MOCK_SIMPLE):
            agent = IdeatorAgent()
            seed = Seed(
                title="Test Article",
                content="Full article markdown content",
                source_url="https://example.com/article",
            )
            result = agent.generate_idea(seed, "Tech interests")
            assert isinstance(result, Idea)
            assert result.title == "Idea Title"
            assert result.summary == "Idea summary text"
            assert result.seed_id == seed.id
            assert result.source_url == "https://example.com/article"
            assert result.status == IdeaStatus.pending

    def test_generate_idea_dry_run(self):
        with _with_side(MOCK_SIMPLE):
            agent = IdeatorAgent()
            seed = Seed(title="Test", content="Content")
            result = agent.generate_idea(seed, "Interests", dry_run=True)
            assert isinstance(result, str)
            assert result == MOCK_SIMPLE

    def test_generate_idea_includes_content_in_prompt(self):
        with _with_side(MOCK_SIMPLE) as mock_run:
            agent = IdeatorAgent()
            seed = Seed(
                title="Article Title",
                content="Article body",
                source_url="https://example.com/a",
            )
            agent.generate_idea(seed, "AI, ML")
            prompt = mock_run.call_args[0][0]
            assert "Article Title" in prompt
            assert "Article body" in prompt
            assert "https://example.com/a" in prompt
            assert "AI, ML" in prompt

    def test_generate_idea_no_url(self):
        with _with_side(MOCK_SIMPLE):
            agent = IdeatorAgent()
            seed = Seed(title="No URL", content="Content here")
            result = agent.generate_idea(seed, "Interests")
            assert isinstance(result, Idea)
            assert result.source_url is None
