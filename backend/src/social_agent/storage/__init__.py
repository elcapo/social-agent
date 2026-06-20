"""Persistence layer for social_agent.

Exposes the repository factory (`factory.py`) and re-exports the repository
Protocols so callers can do::

    from social_agent.storage import get_draft_repository, DraftRepository

Two backends are supported and selectable via `settings.storage_backend`:
- ``"markdown"`` (default): file-based `MarkdownStore` wrappers.
- ``"sqlite"``: SQLAlchemy 2.0 sync repositories.
"""

from social_agent.storage.factory import (
    get_draft_repository,
    get_idea_repository,
    get_seed_repository,
    get_source_repository,
    reset_factory_cache,
)
from social_agent.storage.repositories import (
    DraftRepository,
    IdeaRepository,
    Repository,
    SeedRepository,
    SourceRepository,
)

__all__ = [
    "Repository",
    "SourceRepository",
    "SeedRepository",
    "IdeaRepository",
    "DraftRepository",
    "get_source_repository",
    "get_seed_repository",
    "get_idea_repository",
    "get_draft_repository",
    "reset_factory_cache",
]
