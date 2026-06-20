"""Markdown-backed implementations of the specific repository Protocols.

`MarkdownStore` already satisfies the generic `Repository[T]` Protocol by duck
typing (`save`/`get`/`list`/`delete`/`count`). The entity-specific Protocols
(`SourceRepository`, `SeedRepository`, `IdeaRepository`, `DraftRepository`)
require extra query methods that don't make sense on a generic `MarkdownStore`.

Instead of polluting `MarkdownStore` with type-specific methods, these thin
subclasses inherit all the Markdown behavior and add just the missing query
methods, implemented as filters over the existing `list()`.

They are selected by `storage/factory.py` when `settings.storage_backend ==
"markdown"` (the default), so the existing 225 tests keep passing while new
code can rely on the repository interfaces.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourceType
from social_agent.storage.markdown_store import MarkdownStore


class MarkdownSourceRepository(MarkdownStore[Source]):
    """MarkdownStore for `Source` that satisfies `SourceRepository`."""

    def list_active(self) -> list[Source]:
        return self.list(filter_fn=lambda s: s.enabled)

    def find_by_type(self, source_type: SourceType) -> list[Source]:
        return self.list(filter_fn=lambda s: s.source_type == source_type)

    def get_by_id(self, source_id: str) -> Optional[Source]:
        return self.get(source_id)


class MarkdownSeedRepository(MarkdownStore[Seed]):
    """MarkdownStore for `Seed` that satisfies `SeedRepository`."""

    def list_by_status(self, status: SeedStatus) -> list[Seed]:
        return self.list(filter_fn=lambda s: s.status == status)

    def list_by_source(self, source_id: str) -> list[Seed]:
        return self.list(filter_fn=lambda s: s.source_id == source_id)


class MarkdownIdeaRepository(MarkdownStore[Idea]):
    """MarkdownStore for `Idea` that satisfies `IdeaRepository`."""

    def list_by_status(self, status: IdeaStatus) -> list[Idea]:
        return self.list(filter_fn=lambda i: i.status == status)


class MarkdownDraftRepository(MarkdownStore[Draft]):
    """MarkdownStore for `Draft` that satisfies `DraftRepository`."""

    def list_by_platform(self, platform: str) -> list[Draft]:
        return self.list(filter_fn=lambda d: d.platform == platform)

    def list_by_status(self, status: DraftStatus) -> list[Draft]:
        return self.list(filter_fn=lambda d: d.status == status)

    def list_scheduled(
        self,
        since: Optional[datetime] = None,
        status_values: tuple[str, ...] = ("draft",),
    ) -> list[Draft]:
        # Delegate to the parent's existing implementation to keep one source
        # of truth for the scheduling semantics.
        return super().list_scheduled(since=since, status_values=status_values)


__all__ = [
    "MarkdownSourceRepository",
    "MarkdownSeedRepository",
    "MarkdownIdeaRepository",
    "MarkdownDraftRepository",
]
