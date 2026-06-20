"""Tests for the Markdown -> SQLite migration script.

Covers:
- Migrating a full set of items (sources, seeds, ideas, drafts) with FKs
  preserved and IDs unchanged.
- Migrating when some directories are missing (tolerant).
- Idempotency: running the migration twice does not duplicate rows.
- The `social-agent db migrate` CLI command end-to-end.
- Round-trip: data written to Markdown, migrated to SQLite, then read back
  via the SQLAlchemy repositories matches the originals.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourcePriority, SourceType
from social_agent.storage.db import reset_engine
from social_agent.storage.markdown_store import MarkdownStore
from social_agent.storage.migrate_to_sqlite import MigrationReport, migrate
from social_agent.storage.sqlalchemy_repositories import (
    SqlAlchemyDraftRepository,
    SqlAlchemyIdeaRepository,
    SqlAlchemySeedRepository,
    SqlAlchemySourceRepository,
)
from sqlalchemy import create_engine, text


@pytest.fixture
def markdown_data(tmp_path: Path):
    """Populate a tmp data_dir with one of each entity and return the paths."""
    data_dir = tmp_path / "data"
    for sub in ("sources", "seeds", "ideas", "drafts"):
        (data_dir / sub).mkdir(parents=True)

    src_store = MarkdownStore[Source](data_dir / "sources", Source)
    seed_store = MarkdownStore[Seed](data_dir / "seeds", Seed)
    idea_store = MarkdownStore[Idea](data_dir / "ideas", Idea)
    draft_store = MarkdownStore[Draft](data_dir / "drafts", Draft)

    src = Source(
        name="Hacker News",
        source_type=SourceType.rss,
        url="https://hn.example.com/rss",
        priority=SourcePriority.high,
        tags=["tech", "news"],
        config={"max_items": 5},
    )
    src_store.save(src)

    seed = Seed(
        title="Test Article",
        content="Some **markdown** body",
        source_id=src.id,
        source_name="Hacker News",
        tags=["test"],
        status=SeedStatus.approved,
    )
    seed_store.save(seed)

    idea = Idea(
        seed_id=seed.id,
        title="Great Idea",
        summary="A compelling summary.",
        source_url="https://hn.example.com/article",
        status=IdeaStatus.pending,
    )
    idea_store.save(idea)

    draft = Draft(
        idea_id=idea.id,
        platform="twitter",
        content="Hello world!",
        status=DraftStatus.draft,
        media_urls=["https://img.example.com/a.png"],
        media_paths=["/tmp/a.png"],
    )
    draft_store.save(draft)

    return {
        "data_dir": data_dir,
        "src": src,
        "seed": seed,
        "idea": idea,
        "draft": draft,
    }


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch):
    """Point settings at a tmp data_dir and sqlite_path; reset engine after."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "sqlite_path", db_path)
    monkeypatch.setattr(settings, "storage_backend", "sqlite")
    reset_engine()
    yield db_path
    reset_engine()


class TestMigrate:
    def test_full_migration_preserves_ids_and_fks(self, markdown_data, isolated_settings):
        report = migrate(data_dir=markdown_data["data_dir"])
        assert report.sources == 1
        assert report.seeds == 1
        assert report.ideas == 1
        assert report.drafts == 1
        assert report.total == 4

        eng = create_engine(f"sqlite:///{isolated_settings}")
        try:
            with eng.connect() as conn:
                assert conn.execute(text("SELECT COUNT(*) FROM sources")).scalar() == 1
                assert conn.execute(text("SELECT COUNT(*) FROM seeds")).scalar() == 1
                assert conn.execute(text("SELECT COUNT(*) FROM ideas")).scalar() == 1
                assert conn.execute(text("SELECT COUNT(*) FROM drafts")).scalar() == 1

                # IDs preserved
                src_id = conn.execute(text("SELECT id FROM sources")).scalar()
                assert src_id == markdown_data["src"].id
                seed_id = conn.execute(text("SELECT id FROM seeds")).scalar()
                assert seed_id == markdown_data["seed"].id
                idea_id = conn.execute(text("SELECT id FROM ideas")).scalar()
                assert idea_id == markdown_data["idea"].id
                draft_id = conn.execute(text("SELECT id FROM drafts")).scalar()
                assert draft_id == markdown_data["draft"].id

                # FKs preserved
                assert (
                    conn.execute(text("SELECT source_id FROM seeds")).scalar()
                    == markdown_data["src"].id
                )
                assert (
                    conn.execute(text("SELECT seed_id FROM ideas")).scalar()
                    == markdown_data["seed"].id
                )
                assert (
                    conn.execute(text("SELECT idea_id FROM drafts")).scalar()
                    == markdown_data["idea"].id
                )
        finally:
            eng.dispose()

    def test_roundtrip_via_repositories(self, markdown_data, isolated_settings):
        """After migration, the SQLAlchemy repos return the same data."""
        migrate(data_dir=markdown_data["data_dir"])

        from social_agent.storage.db import get_session_factory

        sf = get_session_factory()
        src_repo = SqlAlchemySourceRepository(sf)
        seed_repo = SqlAlchemySeedRepository(sf)
        idea_repo = SqlAlchemyIdeaRepository(sf)
        draft_repo = SqlAlchemyDraftRepository(sf)

        src = src_repo.get(markdown_data["src"].id)
        assert src is not None
        assert src.name == "Hacker News"
        assert src.tags == ["tech", "news"]
        assert src.config == {"max_items": 5}

        seed = seed_repo.get(markdown_data["seed"].id)
        assert seed is not None
        assert seed.title == "Test Article"
        assert seed.status == SeedStatus.approved
        assert seed.source_id == markdown_data["src"].id

        idea = idea_repo.get(markdown_data["idea"].id)
        assert idea is not None
        assert idea.title == "Great Idea"
        assert idea.seed_id == markdown_data["seed"].id

        draft = draft_repo.get(markdown_data["draft"].id)
        assert draft is not None
        assert draft.platform == "twitter"
        assert draft.media_urls == ["https://img.example.com/a.png"]
        assert draft.media_paths == ["/tmp/a.png"]
        assert draft.idea_id == markdown_data["idea"].id

    def test_idempotent_no_duplicates(self, markdown_data, isolated_settings):
        """Running migrate twice should not create duplicate rows."""
        migrate(data_dir=markdown_data["data_dir"])
        migrate(data_dir=markdown_data["data_dir"])

        eng = create_engine(f"sqlite:///{isolated_settings}")
        try:
            with eng.connect() as conn:
                for table in ("sources", "seeds", "ideas", "drafts"):
                    assert conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() == 1
        finally:
            eng.dispose()

    def test_missing_directories_tolerated(self, tmp_path: Path, isolated_settings):
        """Migrating when no Markdown directories exist should succeed with 0."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        report = migrate(data_dir=empty_dir)
        assert report.total == 0
        assert report.sources == 0

    def test_migration_report_str(self):
        r = MigrationReport(sources=2, seeds=3, ideas=1, drafts=4)
        s = str(r)
        assert "10 items" in s
        assert "sources=2" in s
        assert "drafts=4" in s

    def test_multiple_items(self, tmp_path: Path, isolated_settings):
        """Migrate several sources and verify all are present."""
        data_dir = tmp_path / "data"
        (data_dir / "sources").mkdir(parents=True)
        src_store = MarkdownStore[Source](data_dir / "sources", Source)
        for i in range(5):
            src_store.save(
                Source(name=f"src{i}", source_type=SourceType.rss, url=f"http://x/{i}")
            )
        report = migrate(data_dir=data_dir)
        assert report.sources == 5
        assert report.total == 5


class TestMigrateCLI:
    def test_db_migrate_command(self, markdown_data, isolated_settings, monkeypatch):
        """`social-agent db migrate` migrates data via the CLI."""
        from social_agent.cli.commands import cli

        monkeypatch.setattr(settings, "data_dir", markdown_data["data_dir"])
        monkeypatch.setattr(settings, "sqlite_path", isolated_settings)
        reset_engine()

        runner = CliRunner()
        result = runner.invoke(cli, ["db", "migrate"])
        assert result.exit_code == 0, result.output
        assert "4 items migrated" in result.output
        assert "sources=1" in result.output

    def test_db_migrate_with_explicit_paths(self, markdown_data, tmp_path: Path, monkeypatch):
        """`--data-dir` and `--sqlite-path` overrides work."""
        from social_agent.cli.commands import cli

        db_path = tmp_path / "explicit.db"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "db",
                "migrate",
                "--data-dir",
                str(markdown_data["data_dir"]),
                "--sqlite-path",
                str(db_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "4 items migrated" in result.output
        assert db_path.exists()

        reset_engine()
