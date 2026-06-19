from unittest.mock import patch

from social_agent.agents.writer import WriterAgent, _extract_post
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea

MOCK_DRAFT = "Este es un post genial para la plataforma."

RUN_PATH = "social_agent.agents.writer.WriterAgent.run"

PLATFORM_INSTRUCTIONS = "Tono: Directo, técnico pero accesible."


def _make_idea(title="Test Idea", summary="A summary", source_url=None):
    return Idea(
        seed_id="seed_1",
        title=title,
        summary=summary,
        source_url=source_url,
    )


class TestWriterAgent:
    def test_generate_draft_returns_draft(self):
        with patch(RUN_PATH, return_value=MOCK_DRAFT):
            agent = WriterAgent()
            idea = _make_idea()
            draft = agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            assert isinstance(draft, Draft)
            assert draft.idea_id == idea.id
            assert draft.platform == "twitter"
            assert draft.content == MOCK_DRAFT
            assert draft.status == DraftStatus.draft

    def test_generate_draft_dry_run(self):
        with patch(RUN_PATH, return_value=MOCK_DRAFT):
            agent = WriterAgent()
            idea = _make_idea()
            result = agent.generate_draft(
                idea=idea,
                platform="linkedin",
                platform_instructions=PLATFORM_INSTRUCTIONS,
                dry_run=True,
            )
            assert isinstance(result, str)
            assert result == MOCK_DRAFT

    def test_generate_draft_respects_max_chars(self):
        long_text = "a " * 500
        with patch(RUN_PATH, return_value=long_text):
            agent = WriterAgent()
            idea = _make_idea()
            draft = agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
                max_chars=50,
            )
            assert isinstance(draft, Draft)
            assert len(draft.content) <= 50

    def test_generate_draft_includes_idea_info_in_prompt(self):
        with patch(RUN_PATH, return_value="content") as mock_run:
            agent = WriterAgent()
            idea = _make_idea(
                title="My Title",
                summary="My Summary",
                source_url="https://example.com/article",
            )
            agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
                platform_name="Twitter / X",
            )
            prompt = mock_run.call_args[0][0]
            assert "My Title" in prompt
            assert "My Summary" in prompt
            assert "Twitter / X" in prompt
            assert PLATFORM_INSTRUCTIONS in prompt
            assert "https://example.com/article" in prompt

    def test_generate_draft_with_minimal_idea(self):
        with patch(RUN_PATH, return_value="content"):
            agent = WriterAgent()
            idea = _make_idea(title="Minimal", summary="Minimal summary")
            draft = agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            assert isinstance(draft, Draft)
            assert draft.content == "content"

    def test_extract_post_strips_thinking_tags(self):
        raw = "Aquí va mi razonamiento...\n<post>Este es el contenido real del post.</post>"
        assert _extract_post(raw) == "Este es el contenido real del post."

    def test_extract_post_fallback_no_tags(self):
        raw = "Contenido sin etiquetas de post."
        assert _extract_post(raw) == raw

    def test_extract_post_multiline_content(self):
        raw = "<post>\n  Línea 1\n  Línea 2\n</post>"
        assert _extract_post(raw) == "Línea 1\n  Línea 2"

    def test_generate_draft_strips_thinking(self):
        mock_response = "Pensando...\n<post>Contenido final del post</post>"
        with patch(RUN_PATH, return_value=mock_response):
            agent = WriterAgent()
            idea = _make_idea()
            draft = agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            assert draft.content == "Contenido final del post"
