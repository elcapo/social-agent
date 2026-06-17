from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from social_agent.collectors.base import CollectedItem
from social_agent.main import app
from social_agent.models.draft import Draft
from social_agent.models.seed import Seed
from social_agent.models.source import Source
from social_agent.storage.markdown_store import MarkdownStore

MOCK_SEEDS_JSON = """[
  {"title": "API Idea 1", "summary": "Summary 1", "tags": ["tag1"], "source_index": 1},
  {"title": "API Idea 2", "summary": "Summary 2", "tags": ["tag2"], "source_index": 2}
]"""

MOCK_DRAFT = "Post generado por el Writer Agent para pruebas."

MOCK_COLLECTED = [
    CollectedItem(
        title="Article A", content="Body A",
        url="https://example.com/a", source_id="src_test",
        source_name="Test Source",
        published=datetime.now(timezone.utc),
    ),
]


def _patch_stores(tmp_path: Path):
    data_dir = tmp_path / "data"
    for sub in ("sources", "seeds", "drafts"):
        (data_dir / sub).mkdir(parents=True)

    import social_agent.api.router_sources as rs
    import social_agent.api.router_seeds as rse
    import social_agent.api.router_drafts as rd
    import social_agent.api.router_publish as rp

    for mod in (rs, rse, rd, rp):
        mod.DATA_DIR = data_dir

    rs.source_store = MarkdownStore[Source](data_dir / "sources", Source)
    rse.seed_store = MarkdownStore[Seed](data_dir / "seeds", Seed)
    rse.source_store = MarkdownStore[Source](data_dir / "sources", Source)
    rd.draft_store = MarkdownStore[Draft](data_dir / "drafts", Draft)
    rd.seed_store = MarkdownStore[Seed](data_dir / "seeds", Seed)
    rp.draft_store = MarkdownStore[Draft](data_dir / "drafts", Draft)


@pytest.fixture
def client(tmp_path):
    _patch_stores(tmp_path)
    with TestClient(app) as c:
        yield c


# ── Sources ──


class TestSourcesAPI:
    def test_list_sources_empty(self, client):
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_source(self, client):
        resp = client.post("/api/sources", params={
            "name": "Test RSS", "source_type": "rss", "url": "https://example.com/rss",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test RSS"
        assert data["source_type"] == "rss"
        assert data["url"] == "https://example.com/rss"
        assert data["enabled"] is True
        assert "id" in data

    def test_get_source(self, client):
        create = client.post("/api/sources", params={
            "name": "Test", "source_type": "webpage", "url": "https://example.com",
        })
        sid = create.json()["id"]
        resp = client.get(f"/api/sources/{sid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    def test_get_source_not_found(self, client):
        resp = client.get("/api/sources/nonexistent")
        assert resp.status_code == 404

    def test_delete_source(self, client):
        create = client.post("/api/sources", params={
            "name": "Del", "source_type": "manual", "url": "https://example.com",
        })
        sid = create.json()["id"]
        resp = client.delete(f"/api/sources/{sid}")
        assert resp.status_code == 204
        assert client.get(f"/api/sources/{sid}").status_code == 404

    def test_delete_source_not_found(self, client):
        resp = client.delete("/api/sources/nonexistent")
        assert resp.status_code == 404


# ── Seeds ──


class TestSeedsAPI:
    def test_list_seeds_empty(self, client):
        resp = client.get("/api/seeds")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_generate_seeds_no_sources(self, client):
        resp = client.post("/api/seeds/generate", json={
            "interests": "tech",
        })
        assert resp.status_code == 400
        assert "sources" in resp.json()["detail"].lower()

    def test_generate_seeds_success(self, client, tmp_path):
        _create_test_source(client)

        with patch("social_agent.api.router_seeds.RSSCollector.fetch", return_value=MOCK_COLLECTED):
            with patch("social_agent.agents.ideator.IdeatorAgent.run", return_value=MOCK_SEEDS_JSON):
                resp = client.post("/api/seeds/generate", json={
                    "interests": "tech, python",
                })
        assert resp.status_code == 201
        data = resp.json()
        assert "seeds" in data
        assert len(data["seeds"]) == 2
        assert data["seeds"][0]["title"] == "API Idea 1"
        assert data["seeds"][1]["title"] == "API Idea 2"

    def test_generate_seeds_dry_run(self, client):
        _create_test_source(client)

        with patch("social_agent.api.router_seeds.RSSCollector.fetch", return_value=MOCK_COLLECTED):
            with patch("social_agent.agents.ideator.IdeatorAgent.run", return_value=MOCK_SEEDS_JSON):
                resp = client.post("/api/seeds/generate", json={
                    "interests": "tech",
                    "dry_run": True,
                })
        assert resp.status_code == 201
        data = resp.json()
        assert data["raw_response"] is not None
        assert data["seeds"] is None

    def test_get_seed(self, client):
        seed = _create_test_seed(client)
        resp = client.get(f"/api/seeds/{seed['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == seed["id"]

    def test_get_seed_not_found(self, client):
        resp = client.get("/api/seeds/nonexistent")
        assert resp.status_code == 404

    def test_update_seed_status(self, client):
        seed = _create_test_seed(client)
        resp = client.patch(f"/api/seeds/{seed['id']}", json={"status": "discarded"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "discarded"

    def test_update_seed_not_found(self, client):
        resp = client.patch("/api/seeds/nonexistent", json={"status": "discarded"})
        assert resp.status_code == 404


# ── Drafts ──


class TestDraftsAPI:
    def test_list_drafts_empty(self, client):
        resp = client.get("/api/drafts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_generate_drafts_seed_not_found(self, client):
        resp = client.post("/api/drafts/generate", json={
            "seed_id": "nonexistent",
            "platforms": ["twitter"],
        })
        assert resp.status_code == 404

    def test_generate_drafts_success(self, client):
        seed = _create_test_seed(client)

        with patch("social_agent.agents.writer.WriterAgent.run", return_value=MOCK_DRAFT):
            resp = client.post("/api/drafts/generate", json={
                "seed_id": seed["id"],
                "platforms": ["twitter", "linkedin"],
            })
        assert resp.status_code == 201
        data = resp.json()
        assert "drafts" in data
        assert len(data["drafts"]) == 2
        assert data["drafts"][0]["platform"] == "twitter"
        assert data["drafts"][1]["platform"] == "linkedin"

        # Seed should be marked as used
        seed_resp = client.get(f"/api/seeds/{seed['id']}")
        assert seed_resp.json()["status"] == "used"

    def test_generate_drafts_invalid_platform(self, client):
        seed = _create_test_seed(client)
        resp = client.post("/api/drafts/generate", json={
            "seed_id": seed["id"],
            "platforms": ["nonexistent_platform"],
        })
        assert resp.status_code == 400
        assert "unknown" in resp.json()["detail"].lower()

    def test_generate_drafts_dry_run(self, client):
        seed = _create_test_seed(client)

        with patch("social_agent.agents.writer.WriterAgent.run", return_value=MOCK_DRAFT):
            resp = client.post("/api/drafts/generate", json={
                "seed_id": seed["id"],
                "platforms": ["twitter"],
                "dry_run": True,
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["raw_responses"] is not None
        assert "twitter" in data["raw_responses"]
        assert data["drafts"] is None

    def test_get_draft(self, client):
        draft = _create_test_draft(client)
        resp = client.get(f"/api/drafts/{draft['id']}")
        assert resp.status_code == 200

    def test_get_draft_not_found(self, client):
        resp = client.get("/api/drafts/nonexistent")
        assert resp.status_code == 404

    def test_update_draft_status(self, client):
        draft = _create_test_draft(client)
        resp = client.patch(f"/api/drafts/{draft['id']}", json={"status": "approved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_update_draft_content_resets_status(self, client):
        draft = _create_test_draft(client)
        client.patch(f"/api/drafts/{draft['id']}", json={"status": "approved"})
        resp = client.patch(f"/api/drafts/{draft['id']}", json={"content": "new content"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "new content"
        assert resp.json()["status"] == "draft"


# ── Publish ──


class TestPublishAPI:
    def test_publish_draft(self, client):
        draft = _create_test_draft(client)
        client.patch(f"/api/drafts/{draft['id']}", json={"status": "approved"})
        resp = client.post(f"/api/publish/{draft['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"
        assert resp.json()["published_at"] is not None

    def test_publish_not_approved(self, client):
        draft = _create_test_draft(client)
        resp = client.post(f"/api/publish/{draft['id']}")
        assert resp.status_code == 400
        assert "approved" in resp.json()["detail"]

    def test_publish_not_found(self, client):
        resp = client.post("/api/publish/nonexistent")
        assert resp.status_code == 404

    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ── Helpers ──


def _create_test_source(client) -> dict:
    resp = client.post("/api/sources", params={
        "name": "Test Source",
        "source_type": "rss",
        "url": "https://example.com/rss",
        "priority": 2,
    })
    return resp.json()


def _create_test_seed(client) -> dict:
    _create_test_source(client)

    with patch("social_agent.api.router_seeds.RSSCollector.fetch", return_value=MOCK_COLLECTED):
        with patch("social_agent.agents.ideator.IdeatorAgent.run", return_value=MOCK_SEEDS_JSON):
            resp = client.post("/api/seeds/generate", json={
                "interests": "tech, python",
            })

    seeds = resp.json().get("seeds", [])
    return seeds[0] if seeds else {}


def _create_test_draft(client) -> dict:
    seed = _create_test_seed(client)

    with patch("social_agent.agents.writer.WriterAgent.run", return_value=MOCK_DRAFT):
        resp = client.post("/api/drafts/generate", json={
            "seed_id": seed["id"],
            "platforms": ["twitter"],
        })

    drafts = resp.json().get("drafts", [])
    return drafts[0] if drafts else {}
