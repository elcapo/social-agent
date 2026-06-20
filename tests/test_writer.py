from unittest.mock import patch

from social_agent.agents.writer import WriterAgent, _effective_length, _parse_post
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea

MOCK_DRAFT = "Este es un post genial para la plataforma."

RUN_PATH = "social_agent.agents.writer.WriterAgent.run"

PLATFORM_INSTRUCTIONS = "Tono: Directo, técnico pero accesible."


def _make_idea(title="Test Idea", summary="A summary", source_url=None, comment=None):
    return Idea(
        seed_id="seed_1",
        title=title,
        summary=summary,
        source_url=source_url,
        comment=comment,
    )


class TestWriterAgent:
    def test_generate_draft_returns_draft(self):
        with patch(RUN_PATH, return_value='{"post": "' + MOCK_DRAFT + '"}'):
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
        with patch(RUN_PATH, return_value="raw response"):
            agent = WriterAgent()
            idea = _make_idea()
            result = agent.generate_draft(
                idea=idea,
                platform="linkedin",
                platform_instructions=PLATFORM_INSTRUCTIONS,
                dry_run=True,
            )
            assert isinstance(result, str)
            assert result == "raw response"

    def test_generate_draft_respects_max_chars(self):
        long_text = "a " * 500
        with patch(RUN_PATH, return_value='{"post": "' + long_text + '"}'):
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
        with patch(RUN_PATH, return_value='{"post": "content"}') as mock_run:
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
        with patch(RUN_PATH, return_value='{"post": "content"}'):
            agent = WriterAgent()
            idea = _make_idea(title="Minimal", summary="Minimal summary")
            draft = agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            assert isinstance(draft, Draft)
            assert draft.content == "content"

    def test_parse_post_extracts_post_field(self):
        raw = '{"post": "Contenido real del post"}'
        assert _parse_post(raw) == "Contenido real del post"

    def test_parse_post_fallback_no_json(self):
        raw = "Texto plano sin json"
        assert _parse_post(raw) == raw

    def test_parse_post_fallback_missing_field(self):
        raw = '{"other": "value"}'
        assert _parse_post(raw) == raw

    def test_generate_draft_parses_json(self):
        mock_response = '{"post": "Contenido final del post"}'
        with patch(RUN_PATH, return_value=mock_response):
            agent = WriterAgent()
            idea = _make_idea()
            draft = agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            assert draft.content == "Contenido final del post"

    def test_effective_length_counts_urls_as_23(self):
        text = "Mira esto: https://example.com/muy-largo-url"
        url_len = len("https://example.com/muy-largo-url")
        expected = len(text) - url_len + 23
        assert _effective_length(text) == expected

    def test_generate_draft_includes_comment_in_prompt(self):
        with patch(RUN_PATH, return_value='{"post": "content"}') as mock_run:
            agent = WriterAgent()
            idea = _make_idea(
                title="My Title",
                summary="My Summary",
                comment="estaré probando este modelo esta semana",
                source_url="https://example.com/article",
            )
            agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
                platform_name="Twitter / X",
            )
            prompt = mock_run.call_args[0][0]
            assert "estaré probando este modelo esta semana" in prompt
            assert "Comentario del autor" in prompt
            assert "Resumen de la noticia (fiel al artículo original)" in prompt

    def test_generate_draft_omits_comment_section_when_empty(self):
        with patch(RUN_PATH, return_value='{"post": "content"}') as mock_run:
            agent = WriterAgent()
            idea = _make_idea(title="T", summary="S")
            assert idea.comment is None
            agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            prompt = mock_run.call_args[0][0]
            assert "Comentario del autor" not in prompt
            assert "Resumen de la noticia (fiel al artículo original)" in prompt

    def test_generate_draft_omits_comment_section_when_blank(self):
        with patch(RUN_PATH, return_value='{"post": "content"}') as mock_run:
            agent = WriterAgent()
            idea = _make_idea(title="T", summary="S", comment="   \n  ")
            agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            prompt = mock_run.call_args[0][0]
            assert "Comentario del autor" not in prompt

    def test_generate_draft_distinguishes_summary_and_comment(self):
        with patch(RUN_PATH, return_value='{"post": "content"}') as mock_run:
            agent = WriterAgent()
            idea = _make_idea(
                title="Modelo abierto",
                summary="Resumen neutro de la noticia",
                comment="empieza narrando la publicación e indicando pesos abiertos",
            )
            agent.generate_draft(
                idea=idea,
                platform="twitter",
                platform_instructions=PLATFORM_INSTRUCTIONS,
            )
            prompt = mock_run.call_args[0][0]
            assert "Resumen neutro de la noticia" in prompt
            assert "empieza narrando la publicación e indicando pesos abiertos" in prompt
            idx_summary = prompt.index("Resumen neutro de la noticia")
            idx_comment = prompt.index("empieza narrando la publicación e indicando pesos abiertos")
            assert idx_summary < idx_comment
            assert prompt.count("Comentario del autor") == 1
            assert prompt.count("Resumen de la noticia") == 1
