"""SQLAlchemy 2.0 sync implementations of the repository Protocols.

Each repository wraps a `sessionmaker[Session]` (or a single `Session`) and
maps between the ORM rows (`storage.db`) and the Pydantic domain models
(`social_agent.models`). All operations are synchronous and run within a
short-lived session that is closed at the end of each method.

The constructors accept either a `sessionmaker` (preferred: a fresh session
per operation) or a raw `Session` (useful for tests that want to share a
single transaction / in-memory DB).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Union
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourcePriority, SourceType
from social_agent.storage.db import (
    DraftORM,
    IdeaORM,
    SeedORM,
    SourceORM,
)

SessionFactory = Union[sessionmaker[Session], Session]


def _new_id(prefix: str) -> str:
    """Return a prefixed UUID v4 id (e.g. ``draft_<uuid>``)."""
    return f"{prefix}_{uuid4().hex}"


def _ensure_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Re-attach UTC tzinfo to naive datetimes returned by SQLite/pysqlite.

    SQLite stores datetimes as ISO strings; pysqlite parses them back as naive
    ``datetime`` objects even when the column is declared ``DATETIME(timezone=True)``.
    To preserve the domain invariant that all timestamps are timezone-aware UTC,
    naive values are interpreted as UTC.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _session(session_factory: SessionFactory) -> _SessionCtx:
    return _SessionCtx(session_factory)


class _SessionCtx:
    """Context manager that yields a `Session`.

    If `session_factory` is a `Session`, it is yielded as-is and not closed
    (caller owns its lifecycle — useful for tests). If it is a
    `sessionmaker`, a fresh session is opened and closed on exit.
    """

    def __init__(self, session_factory: SessionFactory):
        self._factory = session_factory
        self._session: Optional[Session] = None
        self._owns = False

    def __enter__(self) -> Session:
        if isinstance(self._factory, Session):
            self._session = self._factory
            self._owns = False
        else:
            self._session = self._factory()
            self._owns = True
        return self._session

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._owns and self._session is not None:
            self._session.close()


# ── Source ──────────────────────────────────────────────────────────────────


class SqlAlchemySourceRepository:
    """SQLAlchemy implementation of `SourceRepository`."""

    def __init__(self, session_factory: SessionFactory):
        self._sf = session_factory

    # ── mappers ──
    @staticmethod
    def _to_orm(model: Source, row: Optional[SourceORM] = None) -> SourceORM:
        row = row or SourceORM()
        row.id = model.id
        row.name = model.name
        row.source_type = model.source_type.value
        row.url = model.url
        row.priority = model.priority.value
        row.tags = list(model.tags)
        row.config = dict(model.config)
        row.enabled = model.enabled
        row.created_at = model.created_at
        row.last_fetched = model.last_fetched
        return row

    @staticmethod
    def _to_pydantic(row: SourceORM) -> Source:
        return Source(
            id=row.id,
            name=row.name,
            source_type=SourceType(row.source_type),
            url=row.url,
            priority=SourcePriority(row.priority),
            tags=list(row.tags or []),
            config=dict(row.config or {}),
            enabled=row.enabled,
            created_at=_ensure_utc(row.created_at),
            last_fetched=_ensure_utc(row.last_fetched),
        )

    # ── CRUD ──
    def save(self, item: Source) -> SourceORM:
        with _session(self._sf) as s:
            existing = s.get(SourceORM, item.id)
            row = self._to_orm(item, existing)
            if existing is None:
                s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def get(self, item_id: str) -> Optional[Source]:
        with _session(self._sf) as s:
            row = s.get(SourceORM, item_id)
            return self._to_pydantic(row) if row else None

    def get_by_id(self, source_id: str) -> Optional[Source]:
        return self.get(source_id)

    def list(self, filter_fn=None) -> list[Source]:
        with _session(self._sf) as s:
            rows = s.execute(select(SourceORM).order_by(SourceORM.created_at)).scalars().all()
            items = [self._to_pydantic(r) for r in rows]
            return [it for it in items if filter_fn is None or filter_fn(it)]

    def delete(self, item_id: str) -> bool:
        with _session(self._sf) as s:
            row = s.get(SourceORM, item_id)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def count(self) -> int:
        with _session(self._sf) as s:
            return s.execute(select(SourceORM)).scalars().all().__len__()

    # ── specific ──
    def list_active(self) -> list[Source]:
        return self.list(filter_fn=lambda src: src.enabled)

    def find_by_type(self, source_type: SourceType) -> list[Source]:
        return self.list(filter_fn=lambda src: src.source_type == source_type)


# ── Seed ────────────────────────────────────────────────────────────────────


class SqlAlchemySeedRepository:
    """SQLAlchemy implementation of `SeedRepository`."""

    def __init__(self, session_factory: SessionFactory):
        self._sf = session_factory

    @staticmethod
    def _to_orm(model: Seed, row: Optional[SeedORM] = None) -> SeedORM:
        row = row or SeedORM()
        row.id = model.id
        row.title = model.title
        row.content = model.content
        row.source_id = model.source_id
        row.source_url = model.source_url
        row.source_name = model.source_name
        row.tags = list(model.tags)
        row.status = model.status.value
        row.created_at = model.created_at
        return row

    @staticmethod
    def _to_pydantic(row: SeedORM) -> Seed:
        return Seed(
            id=row.id,
            title=row.title,
            content=row.content,
            source_id=row.source_id,
            source_url=row.source_url,
            source_name=row.source_name,
            tags=list(row.tags or []),
            status=SeedStatus(row.status),
            created_at=_ensure_utc(row.created_at),
        )

    def save(self, item: Seed) -> SeedORM:
        with _session(self._sf) as s:
            existing = s.get(SeedORM, item.id)
            row = self._to_orm(item, existing)
            if existing is None:
                s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def get(self, item_id: str) -> Optional[Seed]:
        with _session(self._sf) as s:
            row = s.get(SeedORM, item_id)
            return self._to_pydantic(row) if row else None

    def list(self, filter_fn=None) -> list[Seed]:
        with _session(self._sf) as s:
            rows = s.execute(select(SeedORM).order_by(SeedORM.created_at)).scalars().all()
            items = [self._to_pydantic(r) for r in rows]
            return [it for it in items if filter_fn is None or filter_fn(it)]

    def delete(self, item_id: str) -> bool:
        with _session(self._sf) as s:
            row = s.get(SeedORM, item_id)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def count(self) -> int:
        with _session(self._sf) as s:
            return s.execute(select(SeedORM)).scalars().all().__len__()

    def list_by_status(self, status: SeedStatus) -> list[Seed]:
        return self.list(filter_fn=lambda sd: sd.status == status)

    def list_by_source(self, source_id: str) -> list[Seed]:
        return self.list(filter_fn=lambda sd: sd.source_id == source_id)


# ── Idea ────────────────────────────────────────────────────────────────────


class SqlAlchemyIdeaRepository:
    """SQLAlchemy implementation of `IdeaRepository`."""

    def __init__(self, session_factory: SessionFactory):
        self._sf = session_factory

    @staticmethod
    def _to_orm(model: Idea, row: Optional[IdeaORM] = None) -> IdeaORM:
        row = row or IdeaORM()
        row.id = model.id
        row.seed_id = model.seed_id
        row.title = model.title
        row.summary = model.summary
        row.comment = model.comment
        row.source_url = model.source_url
        row.status = model.status.value
        row.created_at = model.created_at
        return row

    @staticmethod
    def _to_pydantic(row: IdeaORM) -> Idea:
        return Idea(
            id=row.id,
            seed_id=row.seed_id,
            title=row.title,
            summary=row.summary,
            comment=row.comment,
            source_url=row.source_url,
            status=IdeaStatus(row.status),
            created_at=_ensure_utc(row.created_at),
        )

    def save(self, item: Idea) -> IdeaORM:
        with _session(self._sf) as s:
            existing = s.get(IdeaORM, item.id)
            row = self._to_orm(item, existing)
            if existing is None:
                s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def get(self, item_id: str) -> Optional[Idea]:
        with _session(self._sf) as s:
            row = s.get(IdeaORM, item_id)
            return self._to_pydantic(row) if row else None

    def list(self, filter_fn=None) -> list[Idea]:
        with _session(self._sf) as s:
            rows = s.execute(select(IdeaORM).order_by(IdeaORM.created_at)).scalars().all()
            items = [self._to_pydantic(r) for r in rows]
            return [it for it in items if filter_fn is None or filter_fn(it)]

    def delete(self, item_id: str) -> bool:
        with _session(self._sf) as s:
            row = s.get(IdeaORM, item_id)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def count(self) -> int:
        with _session(self._sf) as s:
            return s.execute(select(IdeaORM)).scalars().all().__len__()

    def list_by_status(self, status: IdeaStatus) -> list[Idea]:
        return self.list(filter_fn=lambda i: i.status == status)


# ── Draft ───────────────────────────────────────────────────────────────────


class SqlAlchemyDraftRepository:
    """SQLAlchemy implementation of `DraftRepository`."""

    def __init__(self, session_factory: SessionFactory):
        self._sf = session_factory

    @staticmethod
    def _to_orm(model: Draft, row: Optional[DraftORM] = None) -> DraftORM:
        row = row or DraftORM()
        row.id = model.id
        row.idea_id = model.idea_id
        row.platform = model.platform
        row.content = model.content
        row.status = model.status.value
        row.notes = model.notes
        row.platform_post_id = model.platform_post_id
        row.publish_error = model.publish_error
        row.publish_attempts = model.publish_attempts
        row.media_urls = list(model.media_urls)
        row.media_paths = list(model.media_paths)
        row.created_at = model.created_at
        row.published_at = model.published_at
        row.scheduled_at = model.scheduled_at
        return row

    @staticmethod
    def _to_pydantic(row: DraftORM) -> Draft:
        return Draft(
            id=row.id,
            idea_id=row.idea_id,
            platform=row.platform,
            content=row.content,
            status=DraftStatus(row.status),
            notes=row.notes,
            platform_post_id=row.platform_post_id,
            publish_error=row.publish_error,
            publish_attempts=row.publish_attempts,
            media_urls=list(row.media_urls or []),
            media_paths=list(row.media_paths or []),
            created_at=_ensure_utc(row.created_at),
            published_at=_ensure_utc(row.published_at),
            scheduled_at=_ensure_utc(row.scheduled_at),
        )

    def save(self, item: Draft) -> DraftORM:
        with _session(self._sf) as s:
            existing = s.get(DraftORM, item.id)
            row = self._to_orm(item, existing)
            if existing is None:
                s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def get(self, item_id: str) -> Optional[Draft]:
        with _session(self._sf) as s:
            row = s.get(DraftORM, item_id)
            return self._to_pydantic(row) if row else None

    def list(self, filter_fn=None) -> list[Draft]:
        with _session(self._sf) as s:
            rows = s.execute(select(DraftORM).order_by(DraftORM.created_at)).scalars().all()
            items = [self._to_pydantic(r) for r in rows]
            return [it for it in items if filter_fn is None or filter_fn(it)]

    def delete(self, item_id: str) -> bool:
        with _session(self._sf) as s:
            row = s.get(DraftORM, item_id)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def count(self) -> int:
        with _session(self._sf) as s:
            return s.execute(select(DraftORM)).scalars().all().__len__()

    # ── specific ──
    def list_by_platform(self, platform: str) -> list[Draft]:
        return self.list(filter_fn=lambda d: d.platform == platform)

    def list_by_status(self, status: DraftStatus) -> list[Draft]:
        return self.list(filter_fn=lambda d: d.status == status)

    def list_scheduled(
        self,
        since: Optional[datetime] = None,
        status_values: tuple[str, ...] = ("draft",),
    ) -> list[Draft]:
        cutoff = since if since is not None else datetime.now(timezone.utc)
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        allowed = set(status_values)

        def _due(d: Draft) -> bool:
            if d.scheduled_at is None:
                return False
            sched = d.scheduled_at
            if sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)
            status_val = d.status.value if hasattr(d.status, "value") else d.status
            return status_val in allowed and sched <= cutoff

        return self.list(filter_fn=_due)


__all__ = [
    "SqlAlchemySourceRepository",
    "SqlAlchemySeedRepository",
    "SqlAlchemyIdeaRepository",
    "SqlAlchemyDraftRepository",
]
