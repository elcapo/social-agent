"""Migrate existing Markdown-persisted data into the SQLite database.

Reads every `.md` file under ``<data_dir>/{sources,seeds,ideas,drafts}`` and
inserts the corresponding Pydantic models into the SQLite database via the
SQLAlchemy repositories. Existing IDs are preserved so foreign-key
relationships (seed.source_id -> sources.id, idea.seed_id -> seeds.id,
draft.idea_id -> ideas.id) survive the migration.

Usage (programmatic)::

    from social_agent.storage.migrate_to_sqlite import migrate
    migrate()

Or via CLI::

    social-agent db migrate

The migration is idempotent in the sense that re-running it will upsert each
item (save() updates if the row already exists). It does NOT delete the
original Markdown files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from social_agent.config import settings
from social_agent.models.draft import Draft
from social_agent.models.idea import Idea
from social_agent.models.seed import Seed
from social_agent.models.source import Source
from social_agent.storage.db import get_session_factory, init_db, reset_engine
from social_agent.storage.markdown_store import MarkdownStore
from social_agent.storage.sqlalchemy_repositories import (
    SqlAlchemyDraftRepository,
    SqlAlchemyIdeaRepository,
    SqlAlchemySeedRepository,
    SqlAlchemySourceRepository,
)


@dataclass
class MigrationReport:
    """Summary of a migration run."""

    sources: int = 0
    seeds: int = 0
    ideas: int = 0
    drafts: int = 0

    @property
    def total(self) -> int:
        return self.sources + self.seeds + self.ideas + self.drafts

    def __str__(self) -> str:
        return (
            f"Migration complete: {self.total} items migrated "
            f"(sources={self.sources}, seeds={self.seeds}, "
            f"ideas={self.ideas}, drafts={self.drafts})."
        )


def _load_from_markdown(directory: Path, model_class: type) -> list:
    """Load all items from a MarkdownStore directory, tolerating missing dir."""
    if not directory.exists():
        return []
    store = MarkdownStore(directory, model_class)  # type: ignore[arg-type]
    return store.list()


def migrate(
    data_dir: Optional[Path] = None,
    sqlite_path: Optional[Path] = None,
) -> MigrationReport:
    """Migrate Markdown data into SQLite.

    Args:
        data_dir: Override for ``settings.data_dir`` (defaults to settings).
        sqlite_path: Override for the SQLite file path (defaults to
            ``settings.sqlite_path`` or ``<data_dir>/social_agent.db``).

    Returns:
        A :class:`MigrationReport` with counts per entity.
    """
    base = Path(data_dir) if data_dir else settings.data_dir.resolve()
    if sqlite_path is not None:
        settings.sqlite_path = Path(sqlite_path)

    # Force the SQLite engine to (re)build with the current settings.
    reset_engine()
    init_db()
    session_factory = get_session_factory()

    src_repo = SqlAlchemySourceRepository(session_factory)
    seed_repo = SqlAlchemySeedRepository(session_factory)
    idea_repo = SqlAlchemyIdeaRepository(session_factory)
    draft_repo = SqlAlchemyDraftRepository(session_factory)

    report = MigrationReport()

    # 1) Sources (no FKs)
    for src in _load_from_markdown(base / "sources", Source):
        src_repo.save(src)
        report.sources += 1

    # 2) Seeds (FK -> sources, but FK is nullable so order is safe)
    for seed in _load_from_markdown(base / "seeds", Seed):
        seed_repo.save(seed)
        report.seeds += 1

    # 3) Ideas (FK -> seeds)
    for idea in _load_from_markdown(base / "ideas", Idea):
        idea_repo.save(idea)
        report.ideas += 1

    # 4) Drafts (FK -> ideas)
    for draft in _load_from_markdown(base / "drafts", Draft):
        draft_repo.save(draft)
        report.drafts += 1

    return report


__all__ = ["MigrationReport", "migrate"]
