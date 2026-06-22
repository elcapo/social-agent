"""Repository interface for `Seed` entities."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from social_agent.models.seed import Seed, SeedStatus

from .base import Repository


@runtime_checkable
class SeedRepository(Repository[Seed], Protocol):
    """Repository for `Seed` with seed-specific queries."""

    def list_by_status(self, status: SeedStatus) -> list[Seed]:
        """Return all seeds with the given status."""
        ...

    def list_by_source(self, source_id: str) -> list[Seed]:
        """Return all seeds originating from ``source_id``."""
        ...

    def list_source_urls(self) -> set[str]:
        """Return the set of all non-null ``source_url`` values.

        Used by the automated seed generation to deduplicate against every
        previously collected URL, regardless of seed status. Cheaper than
        ``list()`` because it avoids hydrating full models / content bodies.
        """
        ...
