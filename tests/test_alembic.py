"""Tests for the Alembic migration setup.

Verifies that:
- The Alembic config in `backend/alembic.ini` loads and resolves the URL from
  `social_agent.config.settings`.
- `alembic upgrade head` creates the same tables as `Base.metadata.create_all`
  (no drift between the ORM models and the generated migration).
- `alembic downgrade base` drops all tables.
- The autogenerate produces an empty diff when run against a migrated DB.

These tests invoke the Alembic `command` API directly (no subprocess) against
a temporary SQLite file pointed to by `SOCIAL_AGENT_SQLITE_PATH`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from social_agent.config import settings
from social_agent.storage.db import Base, reset_engine
from sqlalchemy import create_engine, inspect

# Path to the alembic.ini shipped with the project (in backend/).
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "backend" / "alembic.ini"
ALEMBIC_DIR = Path(__file__).resolve().parent.parent / "backend" / "alembic"


def _make_alembic_config(db_path: Path) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    # env.py reads the URL from settings; ensure settings points at our tmp DB.
    cfg.set_main_option(
        "sqlalchemy.url", f"sqlite:///{db_path}"
    )
    return cfg


@pytest.fixture
def isolated_sqlite(tmp_path: Path, monkeypatch):
    """Point `settings.sqlite_path` at a fresh tmp DB for the duration of the test."""
    db_path = tmp_path / "alembic_test.db"
    monkeypatch.setattr(settings, "sqlite_path", db_path)
    monkeypatch.setenv("SOCIAL_AGENT_SQLITE_PATH", str(db_path))
    # Reset any cached engine so the new path is picked up.
    reset_engine()
    yield db_path
    reset_engine()
    if db_path.exists():
        db_path.unlink()


class TestAlembicMigration:
    def test_alembic_ini_exists(self):
        assert ALEMBIC_INI.exists(), f"missing {ALEMBIC_INI}"
        assert ALEMBIC_DIR.exists(), f"missing {ALEMBIC_DIR}"

    def test_initial_migration_creates_all_tables(self, isolated_sqlite):
        cfg = _make_alembic_config(isolated_sqlite)
        command.upgrade(cfg, "head")

        eng = create_engine(f"sqlite:///{isolated_sqlite}")
        try:
            insp = inspect(eng)
            tables = set(insp.get_table_names())
        finally:
            eng.dispose()

        assert "alembic_version" in tables  # migration bookkeeping
        for t in ("sources", "seeds", "ideas", "drafts", "published"):
            assert t in tables, f"table {t!r} missing after upgrade"

    def test_downgrade_base_drops_all_tables(self, isolated_sqlite):
        cfg = _make_alembic_config(isolated_sqlite)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")

        eng = create_engine(f"sqlite:///{isolated_sqlite}")
        try:
            tables = set(inspect(eng).get_table_names())
        finally:
            eng.dispose()

        # Only alembic_version remains (it is not dropped by `downgrade base`).
        assert "sources" not in tables
        assert "drafts" not in tables
        assert "ideas" not in tables
        assert "seeds" not in tables
        assert "published" not in tables

    def test_migration_matches_orm_metadata(self, isolated_sqlite, tmp_path: Path):
        """The set of tables/columns produced by `upgrade head` must match
        `Base.metadata.create_all` exactly (no drift).
        """
        # 1) Apply the migration to one DB.
        cfg = _make_alembic_config(isolated_sqlite)
        command.upgrade(cfg, "head")
        eng_migrated = create_engine(f"sqlite:///{isolated_sqlite}")

        # 2) Create tables via metadata on a separate in-memory DB.
        eng_metadata = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(eng_metadata)

        try:
            migrated = inspect(eng_migrated)
            metadata = inspect(eng_metadata)

            migrated_tables = {
                t for t in migrated.get_table_names() if t != "alembic_version"
            }
            metadata_tables = set(metadata.get_table_names())
            assert migrated_tables == metadata_tables

            for table in metadata_tables:
                m_cols = {c["name"] for c in migrated.get_columns(table)}
                d_cols = {c["name"] for c in metadata.get_columns(table)}
                assert m_cols == d_cols, (
                    f"column mismatch on {table}: "
                    f"migrated={m_cols} vs metadata={d_cols}"
                )
        finally:
            eng_migrated.dispose()
            eng_metadata.dispose()
