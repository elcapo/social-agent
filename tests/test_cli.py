from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from social_agent.cli.commands import cli
from social_agent.config import settings as global_settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea
from social_agent.models.seed import Seed
from social_agent.storage.markdown_store import MarkdownStore


@pytest.fixture
def cli_draft_store(tmp_path: Path) -> MarkdownStore[Draft]:
    store = MarkdownStore[Draft](tmp_path / "drafts", Draft)
    with patch("social_agent.cli.commands.draft_store", store):
        yield store


@pytest.fixture
def cli_idea_store(tmp_path: Path) -> MarkdownStore[Idea]:
    store = MarkdownStore[Idea](tmp_path / "ideas", Idea)
    with patch("social_agent.cli.commands.idea_store", store):
        yield store


@pytest.fixture
def cli_seed_store(tmp_path: Path) -> MarkdownStore[Seed]:
    store = MarkdownStore[Seed](tmp_path / "seeds", Seed)
    with patch("social_agent.cli.commands.seed_store", store):
        yield store


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _default_utc_timezone(monkeypatch):
    """Default ``settings.timezone`` to UTC so existing tests are deterministic.

    Tests that exercise timezone-aware behavior override this by monkeypatching
    ``global_settings.timezone`` to a fixed-offset zone (e.g. ``Africa/Lagos``).
    """
    monkeypatch.setattr(global_settings, "timezone", "UTC")


def _make_draft(store: MarkdownStore[Draft], **kwargs) -> Draft:
    defaults = dict(idea_id="idea_1", platform="twitter", content="Hello world")
    defaults.update(kwargs)
    draft = Draft(**defaults)
    store.save(draft)
    return draft


def _make_idea(store: MarkdownStore[Idea], **kwargs) -> Idea:
    defaults = dict(seed_id="seed_1", title="My Idea", summary="A summary")
    defaults.update(kwargs)
    idea = Idea(**defaults)
    store.save(idea)
    return idea


class TestScheduleSet:
    def test_set_schedule(self, runner, cli_draft_store):
        draft = _make_draft(cli_draft_store)
        result = runner.invoke(
            cli,
            ["schedule", "set", draft.id, "2026-06-20T15:30:00"],
        )
        assert result.exit_code == 0
        assert "scheduled for" in result.output
        restored = cli_draft_store.get(draft.id)
        assert restored.scheduled_at is not None
        assert restored.scheduled_at.tzinfo is not None
        assert restored.status == DraftStatus.approved

    def test_set_schedule_not_found(self, runner, cli_draft_store):
        result = runner.invoke(
            cli,
            ["schedule", "set", "nonexistent", "2026-06-20T15:30:00"],
        )
        assert result.exit_code == 0
        assert "not found" in result.output

    def test_set_schedule_invalid_datetime(self, runner, cli_draft_store):
        draft = _make_draft(cli_draft_store)
        result = runner.invoke(
            cli,
            ["schedule", "set", draft.id, "not-a-date"],
        )
        assert result.exit_code != 0

    def test_set_schedule_published_rejected(self, runner, cli_draft_store):
        draft = _make_draft(cli_draft_store, status=DraftStatus.published)
        result = runner.invoke(
            cli,
            ["schedule", "set", draft.id, "2026-06-20T15:30:00"],
        )
        assert result.exit_code == 0
        assert "already published" in result.output

    def test_set_schedule_promotes_rejected_to_approved(self, runner, cli_draft_store):
        draft = _make_draft(cli_draft_store, status=DraftStatus.rejected)
        result = runner.invoke(
            cli,
            ["schedule", "set", draft.id, "2026-06-20T15:30:00"],
        )
        assert result.exit_code == 0
        assert "scheduled for" in result.output
        restored = cli_draft_store.get(draft.id)
        assert restored.scheduled_at is not None
        assert restored.status == DraftStatus.approved


class TestScheduleList:
    def test_list_empty(self, runner, cli_draft_store):
        result = runner.invoke(
            cli,
            ["schedule", "list"],
        )
        assert result.exit_code == 0
        assert "No scheduled drafts" in result.output

    def test_list_shows_scheduled(self, runner, cli_draft_store):
        draft = _make_draft(
            cli_draft_store,
            scheduled_at=datetime(2026, 6, 20, 15, 30, tzinfo=timezone.utc),
        )
        cli_draft_store.save(draft)
        result = runner.invoke(
            cli,
            ["schedule", "list"],
        )
        assert result.exit_code == 0
        assert draft.id in result.output
        assert "2026-06-20T15:30:00" in result.output


class TestScheduleCancel:
    def test_cancel_schedule(self, runner, cli_draft_store):
        draft = _make_draft(
            cli_draft_store,
            scheduled_at=datetime(2026, 6, 20, 15, 30, tzinfo=timezone.utc),
        )
        cli_draft_store.save(draft)
        result = runner.invoke(
            cli,
            ["schedule", "cancel", draft.id],
        )
        assert result.exit_code == 0
        assert "cancelled" in result.output
        assert cli_draft_store.get(draft.id).scheduled_at is None

    def test_cancel_not_scheduled(self, runner, cli_draft_store):
        draft = _make_draft(cli_draft_store)
        result = runner.invoke(
            cli,
            ["schedule", "cancel", draft.id],
        )
        assert result.exit_code == 0
        assert "not scheduled" in result.output

    def test_cancel_not_found(self, runner, cli_draft_store):
        result = runner.invoke(
            cli,
            ["schedule", "cancel", "nonexistent"],
        )
        assert result.exit_code == 0
        assert "not found" in result.output


class TestSchedulePublish:
    def test_publish_no_due(self, runner, cli_draft_store):
        result = runner.invoke(
            cli,
            ["schedule", "publish"],
        )
        assert result.exit_code == 0
        assert "No drafts due" in result.output

    def test_publish_due_draft(self, runner, cli_draft_store):
        draft = _make_draft(
            cli_draft_store,
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        cli_draft_store.save(draft)

        from social_agent.publishers.base import PublishResult

        patches = [
            patch.object(global_settings, "twitter_api_key", "ck"),
            patch.object(global_settings, "twitter_api_secret", "cs"),
            patch.object(global_settings, "twitter_access_token", "at"),
            patch.object(global_settings, "twitter_access_token_secret", "ats"),
        ]
        for p in patches:
            p.start()
        try:
            with patch(
                "social_agent.scheduler.TwitterPublisher.publish",
                return_value=PublishResult(success=True, platform_post_id="cli_123"),
            ):
                result = runner.invoke(
                    cli,
                    ["schedule", "publish"],
                )
        finally:
            for p in patches:
                p.stop()

        assert result.exit_code == 0
        assert "Published" in result.output
        assert "cli_123" in result.output
        restored = cli_draft_store.get(draft.id)
        assert restored.status == DraftStatus.published
        assert restored.scheduled_at is None

    def test_publish_skips_future(self, runner, cli_draft_store):
        draft = _make_draft(
            cli_draft_store,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        cli_draft_store.save(draft)

        result = runner.invoke(
            cli,
            ["schedule", "publish"],
        )
        assert result.exit_code == 0
        assert "No drafts due" in result.output
        assert cli_draft_store.get(draft.id).status == DraftStatus.draft


class TestScheduleTimezone:
    """Naive datetimes are interpreted as ``settings.timezone`` and stored as UTC."""

    def test_set_schedule_naive_uses_configured_tz(self, runner, cli_draft_store, monkeypatch):
        # Africa/Lagos is UTC+1 year-round (no DST) → deterministic.
        monkeypatch.setattr(global_settings, "timezone", "Africa/Lagos")
        draft = _make_draft(cli_draft_store)
        result = runner.invoke(
            cli,
            ["schedule", "set", draft.id, "2026-06-22T15:30:00"],
        )
        assert result.exit_code == 0
        restored = cli_draft_store.get(draft.id)
        assert restored.scheduled_at == datetime(2026, 6, 22, 14, 30, tzinfo=timezone.utc)
        assert restored.scheduled_at.tzinfo is not None

    def test_set_schedule_explicit_offset_respected(self, runner, cli_draft_store, monkeypatch):
        # An explicit offset must win over the configured timezone.
        monkeypatch.setattr(global_settings, "timezone", "Africa/Lagos")
        draft = _make_draft(cli_draft_store)
        result = runner.invoke(
            cli,
            ["schedule", "set", draft.id, "2026-06-22T15:30:00+03:00"],
        )
        assert result.exit_code == 0
        restored = cli_draft_store.get(draft.id)
        assert restored.scheduled_at == datetime(2026, 6, 22, 12, 30, tzinfo=timezone.utc)

    def test_set_schedule_echo_shows_local_and_utc(self, runner, cli_draft_store, monkeypatch):
        monkeypatch.setattr(global_settings, "timezone", "Africa/Lagos")
        draft = _make_draft(cli_draft_store)
        result = runner.invoke(
            cli,
            ["schedule", "set", draft.id, "2026-06-22T15:30:00"],
        )
        assert result.exit_code == 0
        # Local rendering and UTC rendering both appear in the echo.
        assert "2026-06-22T15:30:00+01:00" in result.output
        assert "2026-06-22T14:30:00+00:00" in result.output

    def test_list_displays_in_configured_tz(self, runner, cli_draft_store, monkeypatch):
        monkeypatch.setattr(global_settings, "timezone", "Africa/Lagos")
        draft = _make_draft(
            cli_draft_store,
            scheduled_at=datetime(2026, 6, 22, 14, 30, tzinfo=timezone.utc),
        )
        cli_draft_store.save(draft)
        result = runner.invoke(
            cli,
            ["schedule", "list"],
        )
        assert result.exit_code == 0
        assert "2026-06-22T15:30:00+01:00" in result.output
        # The raw UTC value must NOT leak into the display.
        assert "2026-06-22T14:30:00" not in result.output


class TestIdeasComment:
    def test_set_comment(self, runner, cli_idea_store):
        idea = _make_idea(cli_idea_store)
        result = runner.invoke(
            cli,
            ["ideas", "comment", idea.id, "estaré probando este modelo esta semana"],
        )
        assert result.exit_code == 0
        assert "Comment set" in result.output
        restored = cli_idea_store.get(idea.id)
        assert restored.comment == "estaré probando este modelo esta semana"

    def test_clear_comment(self, runner, cli_idea_store):
        idea = _make_idea(cli_idea_store, comment="comentario previo")
        result = runner.invoke(
            cli,
            ["ideas", "comment", idea.id, "--clear"],
        )
        assert result.exit_code == 0
        assert "cleared" in result.output
        restored = cli_idea_store.get(idea.id)
        assert restored.comment is None

    def test_comment_without_text_or_clear_errors(self, runner, cli_idea_store):
        idea = _make_idea(cli_idea_store)
        result = runner.invoke(
            cli,
            ["ideas", "comment", idea.id],
        )
        assert result.exit_code == 0
        assert "Provide the comment text" in result.output
        restored = cli_idea_store.get(idea.id)
        assert restored.comment is None

    def test_comment_not_found(self, runner, cli_idea_store):
        result = runner.invoke(
            cli,
            ["ideas", "comment", "nonexistent", "texto"],
        )
        assert result.exit_code == 0
        assert "not found" in result.output


class TestIdeasShow:
    def test_show_with_comment(self, runner, cli_idea_store):
        idea = _make_idea(cli_idea_store, comment="notas del autor")
        result = runner.invoke(cli, ["ideas", "show", idea.id])
        assert result.exit_code == 0
        assert "notas del autor" in result.output
        assert "Comment:" in result.output

    def test_show_without_comment(self, runner, cli_idea_store):
        idea = _make_idea(cli_idea_store)
        result = runner.invoke(cli, ["ideas", "show", idea.id])
        assert result.exit_code == 0
        assert "Comment:" not in result.output


class TestSeedsAdd:
    def test_add_with_scrape(self, runner, cli_seed_store):
        with patch(
            "social_agent.cli.commands.scrape_url",
            return_value=("Scraped Title", "Scraped body in markdown"),
        ):
            result = runner.invoke(cli, ["seeds", "add", "https://example.com/article"])
        assert result.exit_code == 0
        assert "Seed added" in result.output
        seeds = cli_seed_store.list()
        assert len(seeds) == 1
        assert seeds[0].title == "Scraped Title"
        assert seeds[0].content == "Scraped body in markdown"
        assert seeds[0].source_url == "https://example.com/article"
        assert seeds[0].source_name == "example.com (manual)"
        assert seeds[0].source_id is None
        assert seeds[0].tags == []

    def test_add_with_manual_overrides(self, runner, cli_seed_store):
        with patch("social_agent.cli.commands.scrape_url") as mock_scrape:
            result = runner.invoke(cli, [
                "seeds", "add", "https://example.com/article",
                "--title", "Manual Title",
                "--content", "Manual content",
                "--tags", "tech, ai",
            ])
        assert result.exit_code == 0
        assert "Manual Title" in result.output
        seeds = cli_seed_store.list()
        assert len(seeds) == 1
        assert seeds[0].title == "Manual Title"
        assert seeds[0].content == "Manual content"
        assert seeds[0].tags == ["tech", "ai"]
        mock_scrape.assert_not_called()

    def test_add_no_scrape(self, runner, cli_seed_store):
        with patch("social_agent.cli.commands.scrape_url") as mock_scrape:
            result = runner.invoke(cli, [
                "seeds", "add", "https://example.com/article",
                "--no-scrape",
                "--title", "Manual Title",
                "--content", "Manual content",
            ])
        assert result.exit_code == 0
        seeds = cli_seed_store.list()
        assert len(seeds) == 1
        assert seeds[0].title == "Manual Title"
        mock_scrape.assert_not_called()

    def test_add_no_scrape_without_title_errors(self, runner, cli_seed_store):
        with patch("social_agent.cli.commands.scrape_url") as mock_scrape:
            result = runner.invoke(cli, [
                "seeds", "add", "https://example.com/article",
                "--no-scrape",
                "--content", "Some content",
            ])
        assert result.exit_code == 0
        assert "--title is required" in result.output
        mock_scrape.assert_not_called()
        assert len(cli_seed_store.list()) == 0

    def test_add_scrape_failure(self, runner, cli_seed_store):
        with patch(
            "social_agent.cli.commands.scrape_url",
            side_effect=RuntimeError("network error"),
        ):
            result = runner.invoke(cli, ["seeds", "add", "https://example.com/bad"])
        assert result.exit_code == 0
        assert "Failed to scrape" in result.output
        assert "network error" in result.output
        assert len(cli_seed_store.list()) == 0

    def test_add_scrapes_only_when_field_missing(self, runner, cli_seed_store):
        with patch(
            "social_agent.cli.commands.scrape_url",
            return_value=("Scraped Title", "Scraped Content"),
        ) as mock_scrape:
            result = runner.invoke(cli, [
                "seeds", "add", "https://example.com/article",
                "--title", "Manual Title",
            ])
        assert result.exit_code == 0
        seeds = cli_seed_store.list()
        assert seeds[0].title == "Manual Title"
        assert seeds[0].content == "Scraped Content"
        mock_scrape.assert_called_once()

    def test_add_allows_duplicate_url(self, runner, cli_seed_store):
        with patch(
            "social_agent.cli.commands.scrape_url",
            return_value=("Title", "Content"),
        ):
            r1 = runner.invoke(cli, ["seeds", "add", "https://example.com/dup"])
            r2 = runner.invoke(cli, ["seeds", "add", "https://example.com/dup"])
        assert r1.exit_code == 0
        assert r2.exit_code == 0
        seeds = cli_seed_store.list()
        assert len(seeds) == 2
