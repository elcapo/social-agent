"""Factory that builds repositories according to `settings.storage_backend`.

Supported backends:
- ``"markdown"`` (default): MarkdownStore-backed wrappers. No DB required;
  preserves the original file-based persistence and all existing tests.
- ``"sqlite"``: SQLAlchemy 2.0 sync repositories over the SQLite engine from
  `storage.db`. Tables are created on first use.

The factory caches the SQLAlchemy session factory so all repositories share
the same engine across a process.
"""

from __future__ import annotations

from typing import Optional

from social_agent.config import settings
from social_agent.storage.markdown_repositories import (
    MarkdownDraftRepository,
    MarkdownIdeaRepository,
    MarkdownSeedRepository,
    MarkdownSourceRepository,
)
from social_agent.storage.repositories import (
    DraftRepository,
    IdeaRepository,
    SeedRepository,
    SourceRepository,
)
from social_agent.storage.sqlalchemy_repositories import (
    SqlAlchemyDraftRepository,
    SqlAlchemyIdeaRepository,
    SqlAlchemySeedRepository,
    SqlAlchemySourceRepository,
)

# Lazily cached SQLAlchemy session factory (only built for the sqlite backend).
_sqlalchemy_session_factory = None


def _markdown_directory(name: str) -> "object":
    """Return ``<data_dir>/<name>`` as a `Path` (imported lazily)."""
    from pathlib import Path

    return Path(settings.data_dir.resolve()) / name


def _get_sqlalchemy_session_factory():
    """Return the cached SQLAlchemy `sessionmaker`, building it if needed.

    Ensures tables exist on first call.
    """
    global _sqlalchemy_session_factory
    if _sqlalchemy_session_factory is None:
        from social_agent.storage.db import get_session_factory, init_db

        init_db()
        _sqlalchemy_session_factory = get_session_factory()
    return _sqlalchemy_session_factory


def _resolve_backend(backend: Optional[str]) -> str:
    return backend if backend is not None else settings.storage_backend


# ── Public factory functions ────────────────────────────────────────────────


def get_source_repository(backend: Optional[str] = None) -> SourceRepository:
    bk = _resolve_backend(backend)
    if bk == "markdown":
        return MarkdownSourceRepository(_markdown_directory("sources"), _model_source())
    if bk == "sqlite":
        return SqlAlchemySourceRepository(_get_sqlalchemy_session_factory())
    raise ValueError(f"Unknown storage backend: {bk!r}")


def get_seed_repository(backend: Optional[str] = None) -> SeedRepository:
    bk = _resolve_backend(backend)
    if bk == "markdown":
        return MarkdownSeedRepository(_markdown_directory("seeds"), _model_seed())
    if bk == "sqlite":
        return SqlAlchemySeedRepository(_get_sqlalchemy_session_factory())
    raise ValueError(f"Unknown storage backend: {bk!r}")


def get_idea_repository(backend: Optional[str] = None) -> IdeaRepository:
    bk = _resolve_backend(backend)
    if bk == "markdown":
        return MarkdownIdeaRepository(_markdown_directory("ideas"), _model_idea())
    if bk == "sqlite":
        return SqlAlchemyIdeaRepository(_get_sqlalchemy_session_factory())
    raise ValueError(f"Unknown storage backend: {bk!r}")


def get_draft_repository(backend: Optional[str] = None) -> DraftRepository:
    bk = _resolve_backend(backend)
    if bk == "markdown":
        return MarkdownDraftRepository(_markdown_directory("drafts"), _model_draft())
    if bk == "sqlite":
        return SqlAlchemyDraftRepository(_get_sqlalchemy_session_factory())
    raise ValueError(f"Unknown storage backend: {bk!r}")


# ── Lazy model imports (avoid a circular import at module load) ─────────────


def _model_source():
    from social_agent.models.source import Source

    return Source


def _model_seed():
    from social_agent.models.seed import Seed

    return Seed


def _model_idea():
    from social_agent.models.idea import Idea

    return Idea


def _model_draft():
    from social_agent.models.draft import Draft

    return Draft


def reset_factory_cache() -> None:
    """Drop the cached SQLAlchemy session factory (mainly for tests)."""
    global _sqlalchemy_session_factory
    _sqlalchemy_session_factory = None


__all__ = [
    "get_source_repository",
    "get_seed_repository",
    "get_idea_repository",
    "get_draft_repository",
    "reset_factory_cache",
]
