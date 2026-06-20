"""Integration tests: FastAPI routers backed by the SQLite repository.

These exercise the full stack — HTTP endpoints -> factory -> SQLAlchemy
repositories -> SQLite — with ``settings.storage_backend = "sqlite"``. They
verify that switching the backend via config produces the same observable
behavior as the Markdown backend covered by ``test_api.py``.

A fresh in-memory SQLite engine is used per test class (via a sessionmaker
shared with the repositories) so tests are isolated and fast.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from social_agent.config import settings
from social_agent.main import app
from social_agent.storage import factory
from social_agent.storage.db import Base, reset_engine
from social_agent.storage.sqlalchemy_repositories import (
    SqlAlchemyDraftRepository,
    SqlAlchemyIdeaRepository,
    SqlAlchemySeedRepository,
    SqlAlchemySourceRepository,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_backends(tmp_path: Path, monkeypatch) -> Generator[dict, None, None]:
    """Wire every router's ``*_store`` to a fresh SQLite-backed repository.

    Builds an in-memory SQLite engine, creates tables, and patches each
    router module's store attribute with a SQLAlchemy repository. Restores
    settings and the engine cache on teardown.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # share a single connection so :memory: persists
        future=True,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    # Point settings at sqlite so the factory would also pick it up.
    monkeypatch.setattr(settings, "storage_backend", "sqlite")
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "sqlite_path", tmp_path / "integ.db")
    factory.reset_factory_cache()
    reset_engine()

    import social_agent.api.router_drafts as rd
    import social_agent.api.router_ideas as ri
    import social_agent.api.router_publish as rp
    import social_agent.api.router_scheduler as rsc
    import social_agent.api.router_seeds as rse
    import social_agent.api.router_sources as rs

    stores = {
        "sources": SqlAlchemySourceRepository(sf),
        "seeds": SqlAlchemySeedRepository(sf),
        "ideas": SqlAlchemyIdeaRepository(sf),
        "drafts": SqlAlchemyDraftRepository(sf),
    }

    rs.source_store = stores["sources"]
    rse.seed_store = stores["seeds"]
    rse.source_store = stores["sources"]
    ri.seed_store = stores["seeds"]
    ri.idea_store = stores["ideas"]
    rd.draft_store = stores["drafts"]
    rd.idea_store = stores["ideas"]
    rp.draft_store = stores["drafts"]
    rsc.draft_store = stores["drafts"]

    yield stores

    engine.dispose()
    reset_engine()
    factory.reset_factory_cache()


@pytest.fixture
def client(sqlite_backends) -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


# ── Sources ────────────────────────────────────────────────────────────────


class TestSourcesSQLiteAPI:
    def test_create_and_list(self, client):
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        assert resp.json() == []

        resp = client.post(
            "/api/sources",
            params={
                "name": "HN",
                "source_type": "rss",
                "url": "https://hn.example.com/rss",
                "priority": 1,
                "tags": ["tech"],
            },
        )
        assert resp.status_code == 201
        created = resp.json()
        assert created["name"] == "HN"
        assert created["tags"] == ["tech"]
        assert created["enabled"] is True

        resp = client.get("/api/sources")
        assert len(resp.json()) == 1

    def test_get_by_id(self, client):
        resp = client.post(
            "/api/sources",
            params={"name": "S", "source_type": "webpage", "url": "http://s"},
        )
        sid = resp.json()["id"]
        resp = client.get(f"/api/sources/{sid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    def test_get_not_found(self, client):
        resp = client.get("/api/sources/nonexistent")
        assert resp.status_code == 404

    def test_update_source(self, client):
        resp = client.post(
            "/api/sources",
            params={"name": "Old", "source_type": "rss", "url": "http://old"},
        )
        sid = resp.json()["id"]
        resp = client.patch(
            f"/api/sources/{sid}",
            params={"name": "New", "enabled": "false"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"
        assert resp.json()["enabled"] is False

    def test_delete_source(self, client):
        resp = client.post(
            "/api/sources",
            params={"name": "Del", "source_type": "rss", "url": "http://d"},
        )
        sid = resp.json()["id"]
        resp = client.delete(f"/api/sources/{sid}")
        assert resp.status_code == 204
        resp = client.get(f"/api/sources/{sid}")
        assert resp.status_code == 404


# ── Seeds ──────────────────────────────────────────────────────────────────


class TestSeedsSQLiteAPI:
    def test_create_via_store_and_list(self, client, sqlite_backends):
        from social_agent.models.seed import Seed, SeedStatus

        sqlite_backends["seeds"].save(
            Seed(title="Article", content="Body", status=SeedStatus.pending)
        )
        resp = client.get("/api/seeds")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Article"

    def test_get_seed(self, client, sqlite_backends):
        from social_agent.models.seed import Seed

        sqlite_backends["seeds"].save(Seed(title="X", content="Y"))
        sid = sqlite_backends["seeds"].list()[0].id
        resp = client.get(f"/api/seeds/{sid}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "X"

    def test_update_seed_status(self, client, sqlite_backends):
        from social_agent.models.seed import Seed

        sqlite_backends["seeds"].save(Seed(title="S", content="C"))
        sid = sqlite_backends["seeds"].list()[0].id
        resp = client.patch(f"/api/seeds/{sid}", json={"status": "approved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_filter_by_status(self, client, sqlite_backends):
        from social_agent.models.seed import Seed, SeedStatus

        sqlite_backends["seeds"].save(Seed(title="P", content="C", status=SeedStatus.pending))
        sqlite_backends["seeds"].save(Seed(title="A", content="C", status=SeedStatus.approved))
        resp = client.get("/api/seeds", params={"status": "approved"})
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "A"


# ── Drafts + scheduling ────────────────────────────────────────────────────


class TestDraftsSQLiteAPI:
    def test_list_drafts_empty(self, client):
        resp = client.get("/api/drafts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_via_store_and_filter(self, client, sqlite_backends):
        from social_agent.models.draft import Draft, DraftStatus

        sqlite_backends["drafts"].save(
            Draft(idea_id="i1", platform="twitter", content="hi", status=DraftStatus.draft)
        )
        sqlite_backends["drafts"].save(
            Draft(idea_id="i2", platform="linkedin", content="hi", status=DraftStatus.approved)
        )
        resp = client.get("/api/drafts", params={"platform": "twitter"})
        assert len(resp.json()) == 1
        resp = client.get("/api/drafts", params={"status": "approved"})
        assert len(resp.json()) == 1
        assert resp.json()[0]["platform"] == "linkedin"

    def test_update_draft_content(self, client, sqlite_backends):
        from social_agent.models.draft import Draft

        sqlite_backends["drafts"].save(Draft(idea_id="i", platform="twitter", content="old"))
        did = sqlite_backends["drafts"].list()[0].id
        resp = client.patch(f"/api/drafts/{did}", json={"content": "new content"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "new content"

    def test_schedule_and_unschedule(self, client, sqlite_backends):
        from datetime import datetime, timedelta, timezone

        from social_agent.models.draft import Draft, DraftStatus

        sqlite_backends["drafts"].save(
            Draft(idea_id="i", platform="twitter", status=DraftStatus.draft)
        )
        did = sqlite_backends["drafts"].list()[0].id

        when = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        resp = client.post(f"/api/drafts/{did}/schedule", json={"scheduled_at": when})
        assert resp.status_code == 200
        assert resp.json()["scheduled_at"] is not None

        resp = client.get("/api/drafts/scheduled")
        assert len(resp.json()) == 1

        resp = client.post(f"/api/drafts/{did}/unschedule")
        assert resp.status_code == 200
        assert resp.json()["scheduled_at"] is None

    def test_scheduler_run_no_due(self, client):
        resp = client.post("/api/scheduler/run")
        assert resp.status_code == 200
        body = resp.json()
        assert body["published"] == 0
        assert body["failed"] == 0


# ── Ideas ──────────────────────────────────────────────────────────────────


class TestIdeasSQLiteAPI:
    def test_list_and_get(self, client, sqlite_backends):
        from social_agent.models.idea import Idea, IdeaStatus

        sqlite_backends["ideas"].save(
            Idea(seed_id="s1", title="T", summary="S", status=IdeaStatus.pending)
        )
        resp = client.get("/api/ideas")
        assert len(resp.json()) == 1

        iid = sqlite_backends["ideas"].list()[0].id
        resp = client.get(f"/api/ideas/{iid}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "T"

    def test_update_idea(self, client, sqlite_backends):
        from social_agent.models.idea import Idea, IdeaStatus

        sqlite_backends["ideas"].save(
            Idea(seed_id="s", title="Old", summary="S", status=IdeaStatus.pending)
        )
        iid = sqlite_backends["ideas"].list()[0].id
        resp = client.patch(f"/api/ideas/{iid}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_idea_comment(self, client, sqlite_backends):
        from social_agent.models.idea import Idea, IdeaStatus

        sqlite_backends["ideas"].save(
            Idea(seed_id="s", title="T", summary="S", status=IdeaStatus.pending)
        )
        iid = sqlite_backends["ideas"].list()[0].id
        resp = client.patch(
            f"/api/ideas/{iid}",
            json={"comment": "instrucción para el escritor"},
        )
        assert resp.status_code == 200
        assert resp.json()["comment"] == "instrucción para el escritor"
        got = client.get(f"/api/ideas/{iid}")
        assert got.json()["comment"] == "instrucción para el escritor"

    def test_delete_idea(self, client, sqlite_backends):
        from social_agent.models.idea import Idea

        sqlite_backends["ideas"].save(Idea(seed_id="s", title="D", summary="x"))
        iid = sqlite_backends["ideas"].list()[0].id
        resp = client.delete(f"/api/ideas/{iid}")
        assert resp.status_code == 204
        resp = client.get(f"/api/ideas/{iid}")
        assert resp.status_code == 404
