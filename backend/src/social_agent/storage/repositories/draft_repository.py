"""Repository interface for `Draft` entities.

Includes `list_scheduled` — the method the scheduler (`scheduler.py`) relies on
to find drafts whose `scheduled_at` is due. Both `MarkdownStore` (existing) and
`SqlAlchemyDraftRepository` (new) satisfy this `Protocol`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from social_agent.models.draft import Draft, DraftStatus

from .base import Repository


@runtime_checkable
class DraftRepository(Repository[Draft], Protocol):
    """Repository for `Draft` with draft-specific queries."""

    def list_scheduled(
        self,
        since: Optional[datetime] = None,
        status_values: tuple[str, ...] = ("draft",),
    ) -> list[Draft]:
        """Return drafts with a populated ``scheduled_at`` that is due.

        A draft is due when ``scheduled_at`` is not None and
        ``scheduled_at <= since`` (``since`` defaults to now in UTC). Drafts
        whose ``status`` value is not in ``status_values`` are excluded.
        """
        ...

    def list_by_platform(self, platform: str) -> list[Draft]:
        """Return all drafts targeting ``platform``."""
        ...

    def list_by_status(self, status: DraftStatus) -> list[Draft]:
        """Return all drafts with the given status."""
        ...
