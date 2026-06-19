from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from social_agent.cli.commands import cli
from social_agent.config import settings as global_settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.storage.markdown_store import MarkdownStore


@pytest.fixture
def cli_draft_store(tmp_path: Path) -> MarkdownStore[Draft]:
    store = MarkdownStore[Draft](tmp_path / "drafts", Draft)
    with patch("social_agent.cli.commands.draft_store", store):
        yield store


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _make_draft(store: MarkdownStore[Draft], **kwargs) -> Draft:
    defaults = dict(idea_id="idea_1", platform="twitter", content="Hello world")
    defaults.update(kwargs)
    draft = Draft(**defaults)
    store.save(draft)
    return draft


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
        assert restored.status == DraftStatus.draft

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
