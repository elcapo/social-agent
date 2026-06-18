from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from social_agent.agents.ideator import IdeatorAgent
from social_agent.collectors.base import CollectedItem
from social_agent.collectors.rss import RSSCollector
from social_agent.collectors.scraper import WebScraperCollector
from social_agent.collectors.social import LinkedInCollector, TwitterCollector
from social_agent.config import settings
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourceType
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = Path("data")
seed_store = MarkdownStore[Seed](DATA_DIR / "seeds", Seed)
source_store = MarkdownStore[Source](DATA_DIR / "sources", Source)

router = APIRouter(tags=["seeds"])


class GenerateSeedsRequest(BaseModel):
    interests: str
    source_ids: Optional[list[str]] = None
    force: bool = False
    dry_run: bool = False


class GenerateSeedsResponse(BaseModel):
    seeds: list[Seed] | None = None
    raw_response: str | None = None
    skipped: int = 0


class UpdateSeedRequest(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    source_url: Optional[str] = None


def _build_collector(source: Source):
    match source.source_type:
        case SourceType.rss:
            return RSSCollector(source.id, source.name, source.url, source.tags)
        case SourceType.webpage:
            return WebScraperCollector(source.id, source.name, source.url, source.tags)
        case SourceType.social:
            if "twitter" in source.url:
                return TwitterCollector(
                    source.id, source.name, source.url, source.tags,
                    bearer_token=settings.twitter_bearer_token,
                )
            if "linkedin" in source.url:
                return LinkedInCollector(
                    source.id, source.name, source.url, source.tags,
                    access_token=settings.linkedin_access_token,
                )
            return None
        case _:
            return None


@router.get("/seeds")
def list_seeds(status: Optional[str] = None) -> list[Seed]:
    def _filter(s: Seed) -> bool:
        if status and s.status.value != status:
            return False
        return True
    return seed_store.list(filter_fn=_filter)


@router.get("/seeds/{seed_id}")
def get_seed(seed_id: str) -> Seed:
    seed = seed_store.get(seed_id)
    if not seed:
        raise HTTPException(404, f"Seed '{seed_id}' not found")
    return seed


@router.post("/seeds/generate", status_code=201)
def generate_seeds(body: GenerateSeedsRequest) -> GenerateSeedsResponse:
    sources = source_store.list(filter_fn=lambda s: s.enabled)
    if body.source_ids:
        sources = [s for s in sources if s.id in body.source_ids]

    if not sources:
        raise HTTPException(400, "No enabled sources found")

    all_items: list[CollectedItem] = []
    for src in sources:
        collector = _build_collector(src)
        if collector is None:
            continue
        try:
            all_items.extend(collector.fetch())
        except Exception:
            continue

    if not all_items:
        raise HTTPException(400, "No content collected from any source")

    ideator = IdeatorAgent()
    result = ideator.generate_seeds(body.interests, all_items, dry_run=body.dry_run)

    if body.dry_run:
        return GenerateSeedsResponse(raw_response=str(result))

    existing_urls: set[str] = set()
    if not body.force:
        existing = seed_store.list()
        existing_urls = {
            s.source_url for s in existing
            if s.source_url and s.status == SeedStatus.pending
        }

    skipped = 0
    for seed in result:
        if not body.force and seed.source_url and seed.source_url in existing_urls:
            skipped += 1
            continue
        seed_store.save(seed)

    return GenerateSeedsResponse(seeds=result, skipped=skipped)


@router.patch("/seeds/{seed_id}")
def update_seed(seed_id: str, body: UpdateSeedRequest) -> Seed:
    seed = seed_store.get(seed_id)
    if not seed:
        raise HTTPException(404, f"Seed '{seed_id}' not found")

    if body.status:
        seed.status = SeedStatus(body.status)
    if body.title is not None:
        seed.title = body.title
    if body.summary is not None:
        seed.summary = body.summary
    if body.source_url is not None:
        seed.source_url = body.source_url

    seed_store.save(seed)
    return seed
