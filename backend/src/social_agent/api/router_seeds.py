from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from social_agent.collectors.base import CollectedItem
from social_agent.collectors.link_scraper import LinkScraperCollector
from social_agent.collectors.rss import RSSCollector
from social_agent.collectors.scraper import WebScraperCollector
from social_agent.collectors.social import LinkedInCollector, TwitterCollector
from social_agent.config import settings
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourceType
from social_agent.storage import get_seed_repository, get_source_repository
from social_agent.utils import html_to_markdown

DATA_DIR = settings.data_dir.resolve()
seed_store = get_seed_repository()
source_store = get_source_repository()

router = APIRouter(tags=["seeds"])


class GenerateSeedsRequest(BaseModel):
    source_ids: Optional[list[str]] = None
    force: bool = False


class GenerateSeedsResponse(BaseModel):
    seeds: list[Seed]
    skipped: int = 0


class UpdateSeedRequest(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    source_url: Optional[str] = None


def _build_collector(source: Source):
    match source.source_type:
        case SourceType.rss:
            return RSSCollector(source.id, source.name, source.url, source.tags, config=source.config)
        case SourceType.webpage:
            return WebScraperCollector(source.id, source.name, source.url, source.tags)
        case SourceType.link_scraper:
            return LinkScraperCollector(
                source.id, source.name, source.url, source.tags, config=source.config,
            )
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


def _collected_item_to_seed(item: CollectedItem) -> Seed:
    content = html_to_markdown(item.content)
    return Seed(
        title=item.title,
        content=content,
        source_id=item.source_id,
        source_url=item.url,
        source_name=item.source_name,
        tags=item.tags,
        status=SeedStatus.pending,
    )


@router.get("/seeds")
def list_seeds(
    status: Optional[str] = None,
    approved: Optional[bool] = None,
    statuses: Optional[list[str]] = Query(default=None),
    q: Optional[str] = None,
    url: Optional[str] = None,
) -> list[Seed]:
    status_set = set(statuses) if statuses else None
    q_lower = q.strip().lower() if q else None
    url_lower = url.strip().lower() if url else None

    def _filter(s: Seed) -> bool:
        if status_set is not None:
            if s.status.value not in status_set:
                return False
        elif status and s.status.value != status:
            return False
        if approved is not None:
            if approved and s.status != SeedStatus.approved:
                return False
            if not approved and s.status == SeedStatus.approved:
                return False
        if q_lower:
            haystack = f"{s.title} {s.content}".lower()
            if q_lower not in haystack:
                return False
        if url_lower:
            if not s.source_url or url_lower not in s.source_url.lower():
                return False
        return True

    items = seed_store.list(filter_fn=_filter)
    items.sort(key=lambda s: s.created_at or "", reverse=True)
    return items


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

    existing_urls: set[str] = set()
    if not body.force:
        existing = seed_store.list()
        existing_urls = {
            s.source_url for s in existing
            if s.source_url and s.status in (SeedStatus.pending, SeedStatus.approved)
        }

    seeds: list[Seed] = []
    skipped = 0
    for item in all_items:
        if not body.force and item.url and item.url in existing_urls:
            skipped += 1
            continue
        seed = _collected_item_to_seed(item)
        seed_store.save(seed)
        seeds.append(seed)

    return GenerateSeedsResponse(seeds=seeds, skipped=skipped)


@router.patch("/seeds/{seed_id}")
def update_seed(seed_id: str, body: UpdateSeedRequest) -> Seed:
    seed = seed_store.get(seed_id)
    if not seed:
        raise HTTPException(404, f"Seed '{seed_id}' not found")

    if body.status:
        seed.status = SeedStatus(body.status)
    if body.title is not None:
        seed.title = body.title
    if body.source_url is not None:
        seed.source_url = body.source_url

    seed_store.save(seed)
    return seed
