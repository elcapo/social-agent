from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from social_agent.config import settings as global_settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.storage.markdown_store import MarkdownStore


@pytest.fixture
def draft_store(tmp_path: Path) -> MarkdownStore[Draft]:
    return MarkdownStore[Draft](tmp_path / "drafts", Draft)


def _due_draft(store: MarkdownStore[Draft], **kwargs) -> Draft:
    defaults = dict(
        idea_id="i1",
        platform="twitter",
        content="due",
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    defaults.update(kwargs)
    draft = Draft(**defaults)
    store.save(draft)
    return draft


class TestGetPublisher:
    def test_unknown_platform(self):
        from social_agent.scheduler import get_publisher
        assert get_publisher("myspace") is None

    def test_twitter_without_credentials(self):
        from social_agent.scheduler import get_publisher
        patches = [
            patch.object(global_settings, "twitter_api_key", None),
            patch.object(global_settings, "twitter_api_secret", None),
            patch.object(global_settings, "twitter_access_token", None),
            patch.object(global_settings, "twitter_access_token_secret", None),
        ]
        for p in patches:
            p.start()
        try:
            assert get_publisher("twitter") is None
        finally:
            for p in patches:
                p.stop()

    def test_linkedin_without_token(self):
        from social_agent.scheduler import get_publisher
        with patch.object(global_settings, "linkedin_access_token", None):
            assert get_publisher("linkedin") is None


class TestRunOnce:
    def test_no_due_drafts(self, draft_store):
        from social_agent.scheduler import run_once
        assert run_once(draft_store) == []

    def test_publishes_due_draft(self, draft_store):
        from social_agent.publishers.base import PublishResult
        from social_agent.scheduler import run_once

        draft = _due_draft(draft_store)
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
                return_value=PublishResult(success=True, platform_post_id="r1"),
            ):
                results = run_once(draft_store)
        finally:
            for p in patches:
                p.stop()

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].platform_post_id == "r1"
        restored = draft_store.get(draft.id)
        assert restored.status == DraftStatus.published
        assert restored.scheduled_at is None

    def test_failed_publish_marks_failed(self, draft_store):
        from social_agent.publishers.base import PublishResult
        from social_agent.scheduler import run_once

        draft = _due_draft(draft_store)
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
                return_value=PublishResult(success=False, error="boom"),
            ):
                results = run_once(draft_store)
        finally:
            for p in patches:
                p.stop()

        assert results[0].success is False
        assert results[0].error == "boom"
        restored = draft_store.get(draft.id)
        assert restored.status == DraftStatus.failed
        assert restored.publish_error == "boom"

    def test_no_publisher_marks_failed(self, draft_store):
        from social_agent.scheduler import run_once

        draft = _due_draft(draft_store, platform="myspace")
        results = run_once(draft_store)
        assert results[0].success is False
        assert "myspace" in results[0].error
        restored = draft_store.get(draft.id)
        assert restored.status == DraftStatus.failed

    def test_skips_future_draft(self, draft_store):
        from social_agent.scheduler import run_once

        future = Draft(
            idea_id="i1", platform="twitter", content="future",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        draft_store.save(future)
        assert run_once(draft_store) == []
        assert draft_store.get(future.id).status == DraftStatus.draft

    def test_publisher_exception_caught(self, draft_store):
        from social_agent.scheduler import run_once

        draft = _due_draft(draft_store)
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
                side_effect=RuntimeError("network down"),
            ):
                results = run_once(draft_store)
        finally:
            for p in patches:
                p.stop()

        assert results[0].success is False
        assert "network down" in results[0].error
        assert draft_store.get(draft.id).status == DraftStatus.failed


class TestRunLoop:
    def test_loop_runs_max_iterations(self, draft_store):
        from social_agent.scheduler import run_loop

        calls: list = []

        def fake_run_once(store):
            calls.append(store)

        async def noop(*a, **k):
            return None

        with patch("social_agent.scheduler.run_once", side_effect=fake_run_once), \
             patch("asyncio.sleep", side_effect=noop):
            asyncio.run(run_loop(draft_store, interval_seconds=0, max_iterations=3))

        assert len(calls) == 3

    def test_loop_survives_iteration_error(self, draft_store):
        from social_agent.scheduler import run_loop

        call_count = {"n": 0}

        def flaky(store):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("transient")

        async def noop(*a, **k):
            return None

        with patch("social_agent.scheduler.run_once", side_effect=flaky), \
             patch("asyncio.sleep", side_effect=noop):
            asyncio.run(run_loop(draft_store, interval_seconds=0, max_iterations=2))

        assert call_count["n"] == 2
