"""Alembic environment for social_agent.

Wires Alembic to the project's SQLAlchemy 2.0 `Base.metadata` (from
`social_agent.storage.db`) so `alembic revision --autogenerate` detects the
ORM models. The database URL is resolved from `social_agent.config.settings`
(honoring `SOCIAL_AGENT_SQLITE_PATH`, defaulting to `<data_dir>/social_agent.db`)
so a single config source drives both the application and the migrations.

Run from `backend/`:
    alembic upgrade head
    alembic downgrade base
    alembic revision --autogenerate -m "description"
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `backend/src` importable when alembic runs from the backend/ directory
# (the installed package also works, but this lets `alembic` work in dev without
# an editable install).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from social_agent.config import settings  # noqa: E402
from social_agent.storage.db import Base  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate: our ORM models.
target_metadata = Base.metadata


def _resolve_url() -> str:
    """Resolve the SQLite URL from settings, falling back to the ini value."""
    db_path = settings.sqlite_path or (settings.data_dir / "social_agent.db")
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to a script)."""
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a real connection)."""
    cfg = config.get_section(config.config_ini_section, {}) or {}
    cfg["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
