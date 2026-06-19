from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from social_agent.collectors.base import CollectedItem
from social_agent.config import settings as global_settings
from social_agent.main import app
from social_agent.models.draft import Draft
from social_agent.models.idea import Idea
from social_agent.models.seed import Seed
from social_agent.models.source import Source
from social_agent.storage.markdown_store import MarkdownStore

MOCK_IDEAS_JSON = """{"title": "Generated Idea", "summary": "Idea summary from LLM"}"""

MOCK_COLLECTED = [
    CollectedItem(
        title="Article A", content="Body A",
        url="https://example.com/a", source_id="src_test",
        source_name="Test Source",
        published=datetime.now(timezone.utc),
    ),
]

MOCK_DRAFT = "Post generado por el Writer Agent para pruebas."


def _patch_stores(tmp_path: Path):
    data_dir = tmp_path / "data"
    for sub in ("sources", "seeds", "ideas", "drafts"):
        (data_dir / sub).mkdir(parents=True)

    import social_agent.api.router_drafts as rd
    import social_agent.api.router_ideas as ri
    import social_agent.api.router_publish as rp
    import social_agent.api.router_seeds as rse
    import social_agent.api.router_sources as rs

    for mod in (rs, rse, rd, rp):
        mod.DATA_DIR = data_dir

    ri.DATA_DIR = data_dir

    rs.source_store = MarkdownStore[Source](data_dir / "sources", Source)
    rse.seed_store = MarkdownStore[Seed](data_dir / "seeds", Seed)
    rse.source_store = MarkdownStore[Source](data_dir / "sources", Source)
    ri.seed_store = MarkdownStore[Seed](data_dir / "seeds", Seed)
    ri.idea_store = MarkdownStore[Idea](data_dir / "ideas", Idea)
    rd.draft_store = MarkdownStore[Draft](data_dir / "drafts", Draft)
    rd.idea_store = MarkdownStore[Idea](data_dir / "ideas", Idea)
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

    def test_update_source_tags(self, client):
        src = _create_test_source(client)
        resp = client.patch(f"/api/sources/{src['id']}", params={
            "name": src["name"], "source_type": "rss", "url": src["url"],
            "priority": src["priority"], "tags": ["tech", "ai"],
        })
        assert resp.status_code == 200
        assert resp.json()["tags"] == ["tech", "ai"]
        get = client.get(f"/api/sources/{src['id']}")
        assert get.json()["tags"] == ["tech", "ai"]

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

    def test_create_source_with_config(self, client):
        resp = client.post("/api/sources", params={
            "name": "Blog",
            "source_type": "link_scraper",
            "url": "https://example.com/blog",
            "config": '{"url_pattern": "/blog/.+", "max_items": 5}',
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_type"] == "link_scraper"
        assert data["config"] == {"url_pattern": "/blog/.+", "max_items": 5}

    def test_create_source_config_defaults_to_empty(self, client):
        resp = client.post("/api/sources", params={
            "name": "No Config",
            "source_type": "rss",
            "url": "https://example.com/rss",
        })
        assert resp.status_code == 201
        assert resp.json()["config"] == {}

    def test_update_source_config(self, client):
        src = _create_test_source(client)
        resp = client.patch(f"/api/sources/{src['id']}", params={
            "config": '{"full_content": false}',
        })
        assert resp.status_code == 200
        assert resp.json()["config"] == {"full_content": False}

    def test_create_source_with_link_scraper_type(self, client):
        resp = client.post("/api/sources", params={
            "name": "LS Blog",
            "source_type": "link_scraper",
            "url": "https://example.com/blog",
        })
        assert resp.status_code == 201
        assert resp.json()["source_type"] == "link_scraper"


# ── Seeds ──


class TestSeedsAPI:
    def test_list_seeds_empty(self, client):
        resp = client.get("/api/seeds")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_generate_seeds_no_sources(self, client):
        resp = client.post("/api/seeds/generate", json={})
        assert resp.status_code == 400
        assert "sources" in resp.json()["detail"].lower()

    def test_generate_seeds_success(self, client):
        _create_test_source(client)

        with patch(
            "social_agent.api.router_seeds.RSSCollector.fetch",
            return_value=MOCK_COLLECTED,
        ):
            resp = client.post("/api/seeds/generate", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert "seeds" in data
        assert len(data["seeds"]) == 1
        assert data["seeds"][0]["title"] == "Article A"
        assert data["skipped"] == 0

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
        resp = client.patch(f"/api/seeds/{seed['id']}", json={"status": "approved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_update_seed_not_found(self, client):
        resp = client.patch("/api/seeds/nonexistent", json={"status": "discarded"})
        assert resp.status_code == 404

    def test_generate_seeds_skips_duplicate_url(self, client):
        _create_test_source(client)

        with patch(
            "social_agent.api.router_seeds.RSSCollector.fetch",
            return_value=MOCK_COLLECTED,
        ):
            resp1 = client.post("/api/seeds/generate", json={})
        assert resp1.status_code == 201
        assert resp1.json()["skipped"] == 0

        with patch(
            "social_agent.api.router_seeds.RSSCollector.fetch",
            return_value=MOCK_COLLECTED,
        ):
            resp2 = client.post("/api/seeds/generate", json={})
        assert resp2.status_code == 201
        assert resp2.json()["skipped"] == 1
        all_seeds = client.get("/api/seeds").json()
        assert len(all_seeds) == 1

    def test_generate_seeds_force_overrides_dedup(self, client):
        _create_test_source(client)

        with patch(
            "social_agent.api.router_seeds.RSSCollector.fetch",
            return_value=MOCK_COLLECTED,
        ):
            client.post("/api/seeds/generate", json={})

        with patch(
            "social_agent.api.router_seeds.RSSCollector.fetch",
            return_value=MOCK_COLLECTED,
        ):
            resp = client.post("/api/seeds/generate", json={"force": True})
        assert resp.status_code == 201
        assert resp.json()["skipped"] == 0
        assert len(resp.json()["seeds"]) == 1

    def test_generate_seeds_multiple_sources(self, client):
        _create_test_source(client)
        _create_test_source(client)

        with patch(
            "social_agent.api.router_seeds.RSSCollector.fetch",
            return_value=MOCK_COLLECTED,
        ):
            resp = client.post("/api/seeds/generate", json={})
        assert resp.status_code == 201
        assert len(resp.json()["seeds"]) == 2

    def test_list_seeds_filter_by_status(self, client):
        seed = _create_test_seed(client)
        client.patch(f"/api/seeds/{seed['id']}", json={"status": "approved"})
        pending = client.get("/api/seeds", params={"status": "pending"})
        assert len(pending.json()) == 0
        approved = client.get("/api/seeds", params={"status": "approved"})
        assert len(approved.json()) == 1

    def test_list_seeds_filter_by_statuses_multiple(self, client):
        _create_test_source(client)
        items = [
            CollectedItem(
                title="A", content="Body A", url="https://example.com/a",
                source_id="src_test", source_name="Test Source",
                published=datetime.now(timezone.utc),
            ),
            CollectedItem(
                title="B", content="Body B", url="https://example.com/b",
                source_id="src_test", source_name="Test Source",
                published=datetime.now(timezone.utc),
            ),
        ]
        with patch("social_agent.api.router_seeds.RSSCollector.fetch", return_value=items):
            resp = client.post("/api/seeds/generate", json={})
        seeds = resp.json()["seeds"]
        client.patch(f"/api/seeds/{seeds[0]['id']}", json={"status": "approved"})
        client.patch(f"/api/seeds/{seeds[1]['id']}", json={"status": "discarded"})

        result = client.get("/api/seeds", params={"statuses": ["approved", "discarded"]})
        assert result.status_code == 200
        statuses = {s["status"] for s in result.json()}
        assert statuses == {"approved", "discarded"}

    def test_list_seeds_filter_by_statuses_none_shows_all(self, client):
        _create_test_source(client)
        items = [
            CollectedItem(
                title="A", content="Body A", url="https://example.com/a",
                source_id="src_test", source_name="Test Source",
                published=datetime.now(timezone.utc),
            ),
            CollectedItem(
                title="B", content="Body B", url="https://example.com/b",
                source_id="src_test", source_name="Test Source",
                published=datetime.now(timezone.utc),
            ),
        ]
        with patch("social_agent.api.router_seeds.RSSCollector.fetch", return_value=items):
            client.post("/api/seeds/generate", json={})
        resp = client.get("/api/seeds", params={"statuses": []})
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def _generate_with(self, client, title, content, url):
        _create_test_source(client)
        item = CollectedItem(
            title=title, content=content, url=url, source_id="src_test",
            source_name="Test Source", published=datetime.now(timezone.utc),
        )
        with patch("social_agent.api.router_seeds.RSSCollector.fetch", return_value=[item]):
            resp = client.post("/api/seeds/generate", json={})
        return resp.json()["seeds"][0]

    def test_list_seeds_filter_by_keyword_in_title(self, client):
        self._generate_with(client, "AI Ethics Article", "Body about something else",
                            "https://example.com/a")
        resp = client.get("/api/seeds", params={"q": "ethics"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "Ethics" in data[0]["title"]

    def test_list_seeds_filter_by_keyword_in_content(self, client):
        self._generate_with(client, "Some Title", "Deep discussion about machine learning",
                            "https://example.com/a")
        resp = client.get("/api/seeds", params={"q": "machine learning"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_seeds_filter_by_keyword_case_insensitive(self, client):
        self._generate_with(client, "Python Programming", "Body",
                            "https://example.com/a")
        resp = client.get("/api/seeds", params={"q": "PYTHON"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_seeds_filter_by_keyword_no_match(self, client):
        self._generate_with(client, "Some Title", "Body",
                            "https://example.com/a")
        resp = client.get("/api/seeds", params={"q": "nonexistenttermxyz"})
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_seeds_filter_by_url_substring(self, client):
        self._generate_with(client, "A", "Body", "https://blog.example.com/post/1")
        resp = client.get("/api/seeds", params={"url": "blog.example"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_seeds_filter_by_url_case_insensitive(self, client):
        self._generate_with(client, "A", "Body", "https://Example.com/Path")
        resp = client.get("/api/seeds", params={"url": "example.com/path"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_seeds_filter_by_url_no_match(self, client):
        self._generate_with(client, "A", "Body", "https://example.com/a")
        resp = client.get("/api/seeds", params={"url": "nomatch.example"})
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_seeds_filters_combined(self, client):
        _create_test_source(client)
        items = [
            CollectedItem(
                title="AI Future", content="Discuss AI",
                url="https://tech.example.com/x", source_id="src_test",
                source_name="Test Source", published=datetime.now(timezone.utc),
            ),
            CollectedItem(
                title="Other", content="Other body",
                url="https://news.example.com/y", source_id="src_test",
                source_name="Test Source", published=datetime.now(timezone.utc),
            ),
        ]
        with patch("social_agent.api.router_seeds.RSSCollector.fetch", return_value=items):
            r1 = client.post("/api/seeds/generate", json={})
        seeds = r1.json()["seeds"]
        client.patch(f"/api/seeds/{seeds[0]['id']}", json={"status": "approved"})

        resp = client.get("/api/seeds", params={
            "statuses": ["approved"], "q": "ai", "url": "tech.example",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "AI Future"


# ── Ideas ──


class TestIdeasAPI:
    def test_list_ideas_empty(self, client):
        resp = client.get("/api/ideas")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_generate_idea_no_seed(self, client):
        resp = client.post("/api/ideas/generate", json={
            "seed_id": "nonexistent",
            "interests": "tech",
        })
        assert resp.status_code == 404

    def test_generate_idea_seed_not_approved(self, client):
        seed = _create_test_seed(client)
        resp = client.post("/api/ideas/generate", json={
            "seed_id": seed["id"],
            "interests": "tech",
        })
        assert resp.status_code == 400
        assert "approved" in resp.json()["detail"].lower()

    def test_generate_idea_success(self, client):
        seed = _create_test_seed(client)
        client.patch(f"/api/seeds/{seed['id']}", json={"status": "approved"})

        patch_ideator = patch(
            "social_agent.agents.ideator.IdeatorAgent.run",
            return_value=MOCK_IDEAS_JSON,
        )
        with patch_ideator:
            resp = client.post("/api/ideas/generate", json={
                "seed_id": seed["id"],
                "interests": "tech, python",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert "idea" in data
        assert data["idea"]["title"] == "Generated Idea"
        assert data["idea"]["summary"] == "Idea summary from LLM"
        assert data["idea"]["seed_id"] == seed["id"]

        seed_resp = client.get(f"/api/seeds/{seed['id']}")
        assert seed_resp.json()["status"] == "used"

    def test_generate_idea_dry_run(self, client):
        seed = _create_test_seed(client)
        client.patch(f"/api/seeds/{seed['id']}", json={"status": "approved"})

        patch_ideator = patch(
            "social_agent.agents.ideator.IdeatorAgent.run",
            return_value=MOCK_IDEAS_JSON,
        )
        with patch_ideator:
            resp = client.post("/api/ideas/generate", json={
                "seed_id": seed["id"],
                "interests": "tech",
                "dry_run": True,
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["raw_response"] is not None
        assert data["idea"] is None

    def test_get_idea(self, client):
        idea = _create_test_idea(client)
        resp = client.get(f"/api/ideas/{idea['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == idea["id"]

    def test_get_idea_not_found(self, client):
        resp = client.get("/api/ideas/nonexistent")
        assert resp.status_code == 404

    def test_update_idea_status(self, client):
        idea = _create_test_idea(client)
        resp = client.patch(f"/api/ideas/{idea['id']}", json={"status": "discarded"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "discarded"

    def test_update_idea_title(self, client):
        idea = _create_test_idea(client)
        resp = client.patch(f"/api/ideas/{idea['id']}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_idea_not_found(self, client):
        resp = client.patch("/api/ideas/nonexistent", json={"status": "discarded"})
        assert resp.status_code == 404

    def test_delete_idea(self, client):
        idea = _create_test_idea(client)
        resp = client.delete(f"/api/ideas/{idea['id']}")
        assert resp.status_code == 204
        get = client.get(f"/api/ideas/{idea['id']}")
        assert get.status_code == 404


# ── Drafts ──


class TestDraftsAPI:
    def test_list_drafts_empty(self, client):
        resp = client.get("/api/drafts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_generate_drafts_idea_not_found(self, client):
        resp = client.post("/api/drafts/generate", json={
            "idea_id": "nonexistent",
            "platforms": ["twitter"],
        })
        assert resp.status_code == 404

    def test_generate_drafts_success(self, client):
        idea = _create_test_idea(client)

        with patch("social_agent.agents.writer.WriterAgent.run", return_value=MOCK_DRAFT):
            resp = client.post("/api/drafts/generate", json={
                "idea_id": idea["id"],
                "platforms": ["twitter", "linkedin"],
            })
        assert resp.status_code == 201
        data = resp.json()
        assert "drafts" in data
        assert len(data["drafts"]) == 2
        assert data["drafts"][0]["platform"] == "twitter"
        assert data["drafts"][1]["platform"] == "linkedin"

        idea_resp = client.get(f"/api/ideas/{idea['id']}")
        assert idea_resp.json()["status"] == "used"

    def test_generate_drafts_invalid_platform(self, client):
        idea = _create_test_idea(client)
        resp = client.post("/api/drafts/generate", json={
            "idea_id": idea["id"],
            "platforms": ["nonexistent_platform"],
        })
        assert resp.status_code == 400
        assert "unknown" in resp.json()["detail"].lower()

    def test_generate_drafts_dry_run(self, client):
        idea = _create_test_idea(client)

        with patch("social_agent.agents.writer.WriterAgent.run", return_value=MOCK_DRAFT):
            resp = client.post("/api/drafts/generate", json={
                "idea_id": idea["id"],
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

    def test_attach_media_to_draft(self, client):
        draft = _create_test_draft(client)
        resp = client.post(
            f"/api/drafts/{draft['id']}/attach-media",
            json={"media_urls": ["https://example.com/img.jpg"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "https://example.com/img.jpg" in data["media_urls"]

    def test_attach_media_appends(self, client):
        draft = _create_test_draft(client)
        client.post(
            f"/api/drafts/{draft['id']}/attach-media",
            json={"media_urls": ["https://example.com/img1.jpg"]},
        )
        resp = client.post(
            f"/api/drafts/{draft['id']}/attach-media",
            json={"media_urls": ["https://example.com/img2.jpg"]},
        )
        assert resp.status_code == 200
        assert resp.json()["media_urls"] == [
            "https://example.com/img1.jpg",
            "https://example.com/img2.jpg",
        ]

    def test_attach_media_draft_not_found(self, client):
        resp = client.post(
            "/api/drafts/nonexistent/attach-media",
            json={"media_urls": ["https://example.com/img.jpg"]},
        )
        assert resp.status_code == 404

    def test_update_draft_media_urls(self, client):
        draft = _create_test_draft(client)
        resp = client.patch(
            f"/api/drafts/{draft['id']}",
            json={"media_urls": ["https://example.com/img.jpg"]},
        )
        assert resp.status_code == 200
        assert resp.json()["media_urls"] == ["https://example.com/img.jpg"]

    def test_upload_media_file(self, client, tmp_path):
        draft = _create_test_draft(client)

        import io
        file_content = b"fake_image_content"
        resp = client.post(
            f"/api/drafts/{draft['id']}/upload-media",
            files={"file": ("test.png", io.BytesIO(file_content), "image/png")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["media_paths"]) == 1
        assert data["media_paths"][0].endswith("test.png")

    def test_upload_media_file_draft_not_found(self, client):
        import io
        resp = client.post(
            "/api/drafts/nonexistent/upload-media",
            files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
        )
        assert resp.status_code == 404

    def test_publish_with_uploaded_media(self, client):
        draft = _create_test_draft(client)

        import io
        upload_resp = client.post(
            f"/api/drafts/{draft['id']}/upload-media",
            files={"file": ("test.png", io.BytesIO(b"fake_png"), "image/png")},
        )
        assert upload_resp.status_code == 201
        assert len(upload_resp.json()["media_paths"]) == 1

        client.patch(f"/api/drafts/{draft['id']}", json={"status": "approved"})

        patches = [
            patch.object(global_settings, "twitter_api_key", "ck"),
            patch.object(global_settings, "twitter_api_secret", "cs"),
            patch.object(global_settings, "twitter_access_token", "at"),
            patch.object(global_settings, "twitter_access_token_secret", "ats"),
        ]
        for p in patches:
            p.start()

        from social_agent.publishers.base import PublishResult

        with patch(
            "social_agent.api.router_publish.TwitterPublisher.publish",
            return_value=PublishResult(success=True, platform_post_id="e2e_123"),
        ) as mock_publish:
            resp = client.post(f"/api/publish/{draft['id']}")

        for p in patches:
            p.stop()

        assert resp.status_code == 200
        assert resp.json()["status"] == "published"
        mock_publish.assert_called_once()
        call_draft = mock_publish.call_args[0][0]
        assert len(call_draft.media_paths) == 1
        assert "test.png" in call_draft.media_paths[0]

    def test_upload_media_appends_to_existing(self, client, tmp_path):
        draft = _create_test_draft(client)

        import io
        client.post(
            f"/api/drafts/{draft['id']}/upload-media",
            files={"file": ("img1.png", io.BytesIO(b"data1"), "image/png")},
        )
        resp = client.post(
            f"/api/drafts/{draft['id']}/upload-media",
            files={"file": ("img2.png", io.BytesIO(b"data2"), "image/png")},
        )
        assert resp.status_code == 201
        assert len(resp.json()["media_paths"]) == 2


# ── Publish ──


class TestPublishAPI:
    def test_publish_draft(self, client):
        draft = _create_test_draft(client)
        client.patch(f"/api/drafts/{draft['id']}", json={"status": "approved"})

        patches = [
            patch.object(global_settings, "twitter_api_key", "ck"),
            patch.object(global_settings, "twitter_api_secret", "cs"),
            patch.object(global_settings, "twitter_access_token", "at"),
            patch.object(global_settings, "twitter_access_token_secret", "ats"),
        ]
        for p in patches:
            p.start()

        from social_agent.publishers.base import PublishResult

        with patch(
            "social_agent.api.router_publish.TwitterPublisher.publish",
            return_value=PublishResult(success=True, platform_post_id="12345"),
        ):
            resp = client.post(f"/api/publish/{draft['id']}")

        for p in patches:
            p.stop()

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "published"
        assert data["platform_post_id"] == "12345"
        assert data["published_at"] is not None

    def test_publish_no_credentials(self, client):
        draft = _create_test_draft(client)
        client.patch(f"/api/drafts/{draft['id']}", json={"status": "approved"})

        patches = [
            patch.object(global_settings, "twitter_api_key", None),
            patch.object(global_settings, "twitter_api_secret", None),
            patch.object(global_settings, "twitter_access_token", None),
            patch.object(global_settings, "twitter_access_token_secret", None),
        ]
        for p in patches:
            p.start()

        resp = client.post(f"/api/publish/{draft['id']}")

        for p in patches:
            p.stop()

        assert resp.status_code == 400
        assert "No publisher configured" in resp.json()["detail"]

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
        resp = client.post("/api/seeds/generate", json={})

    seeds = resp.json().get("seeds", [])
    return seeds[0] if seeds else {}


def _create_test_idea(client) -> dict:
    seed = _create_test_seed(client)
    client.patch(f"/api/seeds/{seed['id']}", json={"status": "approved"})

    with patch("social_agent.agents.ideator.IdeatorAgent.run", return_value=MOCK_IDEAS_JSON):
        resp = client.post("/api/ideas/generate", json={
            "seed_id": seed["id"],
            "interests": "tech",
        })

    idea = resp.json().get("idea", {})
    return idea


def _create_test_draft(client) -> dict:
    idea = _create_test_idea(client)

    with patch("social_agent.agents.writer.WriterAgent.run", return_value=MOCK_DRAFT):
        resp = client.post("/api/drafts/generate", json={
            "idea_id": idea["id"],
            "platforms": ["twitter"],
        })

    drafts = resp.json().get("drafts", [])
    return drafts[0] if drafts else {}
