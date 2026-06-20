"""SQLAlchemy 2.0 ORM models and engine setup for the SQLite backend.

Defines the schema that mirrors the Pydantic domain models (Source, Seed, Idea,
Draft) plus a `published` history table. Uses sync sessions via `sessionmaker`.

The engine is lazily built from `settings.sqlite_path` (defaults to
`<data_dir>/social_agent.db`) with `check_same_thread=False` so it can be shared
across FastAPI request workers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from social_agent.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _default_id(prefix: str) -> str:
    """Return a prefixed timestamp-based id (mirrors the Pydantic default)."""
    return f"{prefix}_{_utcnow().timestamp():.6f}"


class SourceORM(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: _default_id("src")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_fetched: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_sources_enabled", "enabled"),)


class SeedORM(Base):
    __tablename__ = "seeds"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: _default_id("seed")
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("sources.id", ondelete="SET NULL")
    )
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (Index("ix_seeds_status", "status"),)


class IdeaORM(Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: _default_id("idea")
    )
    seed_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("seeds.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (Index("ix_ideas_status", "status"),)


class DraftORM(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: _default_id("draft")
    )
    idea_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ideas.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(255))
    publish_error: Mapped[Optional[str]] = mapped_column(Text)
    publish_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    media_urls: Mapped[list] = mapped_column(JSON, default=list)
    media_paths: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_drafts_status", "status"),
        Index("ix_drafts_platform", "platform"),
        Index("ix_drafts_scheduled_at", "scheduled_at"),
    )


class PublishedORM(Base):
    """History of successful publications (one row per published draft)."""

    __tablename__ = "published"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    post_url: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


_engine = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def get_engine():
    """Lazily build and cache the global engine.

    Uses `settings.sqlite_path` if set, otherwise `<data_dir>/social_agent.db`.
    `check_same_thread=False` allows sharing the engine across FastAPI workers.
    """
    global _engine
    if _engine is not None:
        return _engine
    db_path = settings.sqlite_path or (settings.data_dir / "social_agent.db")
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the global `sessionmaker` bound to the cached engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), expire_on_commit=False, future=True
        )
    return _SessionLocal


def init_db(engine=None) -> None:
    """Create all tables on the given engine (defaults to the global one)."""
    target = engine if engine is not None else get_engine()
    Base.metadata.create_all(target)


def reset_engine() -> None:
    """Reset the cached engine and session factory (mainly for tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
