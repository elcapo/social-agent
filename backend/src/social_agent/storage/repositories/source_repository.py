"""Repository interface for `Source` entities."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from social_agent.models.source import Source, SourceType

from .base import Repository


@runtime_checkable
class SourceRepository(Repository[Source], Protocol):
    """Repository for `Source` with source-specific queries."""

    def list_active(self) -> list[Source]:
        """Return all enabled sources."""
        ...

    def find_by_type(self, source_type: SourceType) -> list[Source]:
        """Return all sources of the given type (regardless of `enabled`)."""
        ...

    def get_by_id(self, source_id: str) -> Optional[Source]:
        """Alias for ``get``; kept for explicitness in collectors."""
        ...
