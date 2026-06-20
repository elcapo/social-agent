"""Repository interface for `Idea` entities.

Added during Fase 11 to close the gap in the original ROADMAP, which omitted the
`Idea` model even though the pipeline `seed -> idea -> draft` (and
`router_ideas.py`) depends on it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from social_agent.models.idea import Idea, IdeaStatus

from .base import Repository


@runtime_checkable
class IdeaRepository(Repository[Idea], Protocol):
    """Repository for `Idea` with idea-specific queries."""

    def list_by_status(self, status: IdeaStatus) -> list[Idea]:
        """Return all ideas with the given status."""
        ...
