from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from social_agent.collectors.base import CollectedItem
from social_agent.collectors.link_scraper import LinkScraperCollector, scrape_url
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
logger = logging.getLogger(__name__)

_MAX_WORKERS = 5


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


class ScrapeRequest(BaseModel):
    url: str
    renderer: str = "httpx"


class ScrapeResponse(BaseModel):
    title: str
    content: str


class CreateSeedRequest(BaseModel):
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    tags: list[str] = []
    scrape: bool = True
    renderer: str = "httpx"


def _build_collector(source: Source):
    match source.source_type:
        case SourceType.rss:
            return RSSCollector(
                source.id, source.name, source.url, source.tags, config=source.config,
            )
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


def _uses_playwright(source: Source) -> bool:
    """Return True if the source's collector renders with Playwright.

    Playwright is not thread-safe, so sources using it must be fetched
    sequentially rather than through the thread pool.
    """
    renderer = (source.config or {}).get("renderer", "httpx")
    return renderer == "playwright"


def _fetch_one_source(source: Source) -> list[CollectedItem]:
    collector = _build_collector(source)
    if collector is None:
        return []
    try:
        return collector.fetch()
    except Exception:
        logger.exception("Collector for source '%s' (%s) failed", source.id, source.name)
        return []


@router.post("/seeds/generate", status_code=201)
def generate_seeds(body: GenerateSeedsRequest) -> GenerateSeedsResponse:
    sources = source_store.list(filter_fn=lambda s: s.enabled)
    if body.source_ids:
        sources = [s for s in sources if s.id in body.source_ids]

    if not sources:
        raise HTTPException(400, "No enabled sources found")

    # Split sources: Playwright sources must run sequentially (not thread-safe);
    # the rest can be fetched concurrently.
    pw_sources = [s for s in sources if _uses_playwright(s)]
    other_sources = [s for s in sources if not _uses_playwright(s)]

    all_items: list[CollectedItem] = []

    for src in pw_sources:
        all_items.extend(_fetch_one_source(src))

    if other_sources:
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            results = pool.map(_fetch_one_source, other_sources)
            for items in results:
                all_items.extend(items)

    if not all_items:
        raise HTTPException(400, "No content collected from any source")

    existing_urls: set[str] = set()
    if not body.force:
        existing_urls = seed_store.list_source_urls()

    seeds: list[Seed] = []
    skipped = 0
    for item in all_items:
        if not body.force and item.url and item.url in existing_urls:
            skipped += 1
            continue
        seed = _collected_item_to_seed(item)
        seed_store.save(seed)
        seeds.append(seed)
        if item.url:
            existing_urls.add(item.url)

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


@router.post("/seeds/scrape", response_model=ScrapeResponse)
def scrape_article(body: ScrapeRequest) -> ScrapeResponse:
    try:
        title, content = scrape_url(body.url, renderer=body.renderer)
    except Exception as e:
        raise HTTPException(400, f"Failed to scrape URL: {e}")
    return ScrapeResponse(title=title, content=content)


@router.post("/seeds", status_code=201, response_model=Seed)
def create_seed(body: CreateSeedRequest) -> Seed:
    title = body.title
    content = body.content

    if body.scrape and (not title or not content):
        try:
            scraped_title, scraped_content = scrape_url(body.url, renderer=body.renderer)
        except Exception as e:
            raise HTTPException(400, f"Failed to scrape URL: {e}")
        if not title:
            title = scraped_title or body.url
        if not content:
            content = scraped_content

    if not title:
        title = body.url

    parsed = urlparse(body.url)
    domain = parsed.hostname or body.url
    source_name = f"{domain} (manual)"

    seed = Seed(
        title=title,
        content=content or "",
        source_id=None,
        source_url=body.url,
        source_name=source_name,
        tags=body.tags,
        status=SeedStatus.pending,
    )
    seed_store.save(seed)
    return seed
