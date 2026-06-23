from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.publishers.base import BasePublisher, PublishResult
from social_agent.publishers.linkedin import LinkedInPublisher
from social_agent.publishers.twitter import TwitterPublisher
from social_agent.storage.repositories import DraftRepository

logger = logging.getLogger(__name__)


def get_publisher(platform: str) -> Optional[BasePublisher]:
    """Return a configured publisher for ``platform`` or ``None`` if unavailable."""
    if platform == "twitter":
        if not all([
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret,
        ]):
            return None
        return TwitterPublisher(
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_token_secret,
        )
    if platform == "linkedin":
        if not settings.linkedin_access_token:
            return None
        return LinkedInPublisher(
            access_token=settings.linkedin_access_token,
            author_urn=settings.linkedin_author_urn,
        )
    return None


def _apply_result(draft: Draft, result: PublishResult) -> None:
    draft.publish_attempts += 1
    if result.success:
        draft.status = DraftStatus.published
        draft.platform_post_id = result.platform_post_id
        draft.published_at = result.published_at
        draft.publish_error = None
        draft.scheduled_at = None
    else:
        draft.status = DraftStatus.failed
        draft.publish_error = result.error


@dataclass
class ScheduledItemResult:
    draft_id: str
    platform: str
    success: bool
    platform_post_id: Optional[str] = None
    error: Optional[str] = None


def run_once(
    draft_store: DraftRepository,
    since: Optional[datetime] = None,
) -> list[ScheduledItemResult]:
    """Publish every scheduled draft that is due.

    A draft is due when it has a populated ``scheduled_at`` that is not later than
    ``since`` (defaults to now in UTC) and its status is ``approved`` (drafts that
    have not been approved, and already published/failed/rejected drafts, are
    skipped). Each due draft is published through its platform publisher, the
    result is persisted, and a :class:`ScheduledItemResult` is returned
    describing the outcome.
    """
    publishable = (DraftStatus.approved.value,)
    due = draft_store.list_scheduled(since=since, status_values=publishable)
    results: list[ScheduledItemResult] = []

    for draft in due:
        publisher = get_publisher(draft.platform)
        if publisher is None:
            logger.warning("No publisher configured for platform '%s' (draft %s)",
                           draft.platform, draft.id)
            results.append(ScheduledItemResult(
                draft_id=draft.id,
                platform=draft.platform,
                success=False,
                error=f"No publisher configured for platform '{draft.platform}'",
            ))
            draft.status = DraftStatus.failed
            draft.publish_error = results[-1].error
            draft_store.save(draft)
            continue

        try:
            result = publisher.publish(draft)
        except Exception as exc:  # noqa: BLE001 - scheduler must not crash on one failure
            logger.exception("Error publishing scheduled draft %s", draft.id)
            result = PublishResult(success=False, error=str(exc))

        _apply_result(draft, result)
        draft_store.save(draft)
        results.append(ScheduledItemResult(
            draft_id=draft.id,
            platform=draft.platform,
            success=result.success,
            platform_post_id=result.platform_post_id,
            error=result.error,
        ))

    return results


async def run_loop(
    draft_store: DraftRepository,
    interval_seconds: int = 300,
    max_iterations: Optional[int] = None,
) -> None:
    """Background worker that periodically runs :func:`run_once`.

    ``interval_seconds`` defaults to 5 minutes. If ``max_iterations`` is given the
    loop stops after that many cycles (useful for tests); otherwise it runs forever
    until cancelled.
    """
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        try:
            run_once(draft_store)
        except Exception:  # noqa: BLE001 - keep the worker alive
            logger.exception("Scheduler iteration failed")
        iteration += 1
        await asyncio.sleep(interval_seconds)
