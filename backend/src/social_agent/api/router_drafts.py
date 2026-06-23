from __future__ import annotations

import logging
import shutil
from datetime import datetime
from typing import Optional

import frontmatter
from fastapi import APIRouter, HTTPException, Query, UploadFile
from pydantic import BaseModel

from social_agent.agents.writer import WriterAgent
from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import IdeaStatus
from social_agent.storage import get_draft_repository, get_idea_repository
from social_agent.timezone_utils import localize_to_utc

logger = logging.getLogger(__name__)

DATA_DIR = settings.data_dir.resolve()
draft_store = get_draft_repository()
idea_store = get_idea_repository()

router = APIRouter(tags=["drafts"])


class GenerateDraftsRequest(BaseModel):
    idea_id: str
    platforms: list[str]
    dry_run: bool = False


class GenerateDraftsResponse(BaseModel):
    drafts: list[Draft] | None = None
    raw_responses: dict[str, str] | None = None


class UpdateDraftRequest(BaseModel):
    status: Optional[str] = None
    content: Optional[str] = None
    notes: Optional[str] = None
    media_urls: Optional[list[str]] = None


class AttachMediaRequest(BaseModel):
    media_urls: list[str] = []


class ScheduleDraftRequest(BaseModel):
    scheduled_at: datetime


@router.get("/drafts")
def list_drafts(
    platform: Optional[str] = None,
    platforms: Optional[list[str]] = Query(default=None),
    status: Optional[str] = None,
    statuses: Optional[list[str]] = Query(default=None),
    q: Optional[str] = None,
) -> list[Draft]:
    platform_set = set(platforms) if platforms else None
    status_set = set(statuses) if statuses else None
    q_lower = q.strip().lower() if q else None

    def _filter(d: Draft) -> bool:
        if platform_set is not None:
            if d.platform not in platform_set:
                return False
        elif platform and d.platform != platform:
            return False
        if status_set is not None:
            if d.status.value not in status_set:
                return False
        elif status and d.status.value != status:
            return False
        if q_lower:
            haystack = f"{d.content}".lower()
            if q_lower not in haystack:
                return False
        return True
    items = draft_store.list(filter_fn=_filter)
    items.sort(key=lambda d: d.created_at or "", reverse=True)
    return items


@router.get("/drafts/scheduled")
def list_scheduled_drafts() -> list[Draft]:
    return [
        d for d in draft_store.list()
        if d.scheduled_at is not None and d.status == DraftStatus.approved
    ]


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")
    return draft


@router.post("/drafts/generate", status_code=201)
def generate_drafts(body: GenerateDraftsRequest) -> GenerateDraftsResponse:
    idea = idea_store.get(body.idea_id)
    if not idea:
        raise HTTPException(404, f"Idea '{body.idea_id}' not found")

    if idea.status != IdeaStatus.pending:
        raise HTTPException(400, f"Idea is {idea.status.value}, only pending ideas can be used")

    platforms_dir = settings.prompts_dir / "platforms"
    if not platforms_dir.exists():
        raise HTTPException(500, f"Platform prompts directory not found: {platforms_dir}")

    available = {p.stem for p in platforms_dir.glob("*.md")}
    invalid = [p for p in body.platforms if p not in available]
    if invalid:
        raise HTTPException(400, f"Unknown platform(s): {', '.join(invalid)}")

    writer = WriterAgent()
    drafts: list[Draft] = []
    raw_responses: dict[str, str] = {}

    for p in body.platforms:
        path = platforms_dir / f"{p}.md"
        with open(path) as f:
            post = frontmatter.load(f)

        instructions = post.content.strip()
        platform_name = post.metadata.get("title", p)
        max_chars = post.metadata.get("max_chars", 0)

        result = writer.generate_draft(
            idea=idea,
            platform=p,
            platform_instructions=instructions,
            platform_name=platform_name,
            max_chars=max_chars,
            dry_run=body.dry_run,
        )

        if body.dry_run:
            raw_responses[p] = str(result)
        elif result is None:
            raise HTTPException(500, f"LLM returned empty content for platform '{p}' after retry")
        else:
            draft_store.save(result)
            drafts.append(result)

    if not body.dry_run:
        idea.status = IdeaStatus.used
        idea_store.save(idea)

    if body.dry_run:
        return GenerateDraftsResponse(raw_responses=raw_responses)

    return GenerateDraftsResponse(drafts=drafts)


@router.patch("/drafts/{draft_id}")
def update_draft(draft_id: str, body: UpdateDraftRequest) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    if body.status:
        draft.status = DraftStatus(body.status)
    if body.content is not None:
        draft.content = body.content
        if draft.status == DraftStatus.approved:
            draft.status = DraftStatus.draft
    if body.notes is not None:
        draft.notes = body.notes
    if body.media_urls is not None:
        draft.media_urls = body.media_urls

    draft_store.save(draft)
    return draft


@router.post("/drafts/{draft_id}/attach-media")
def attach_media(draft_id: str, body: AttachMediaRequest) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    draft.media_urls.extend(body.media_urls)
    draft_store.save(draft)
    return draft


@router.post("/drafts/{draft_id}/upload-media", status_code=201)
def upload_media(draft_id: str, file: UploadFile) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    media_dir = DATA_DIR / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{draft_id}_{file.filename or 'upload'}"
    dest = media_dir / filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    abs_path = str(dest.resolve())
    logger.info("Uploaded media for draft '%s': %s", draft_id, abs_path)
    draft.media_paths.append(abs_path)
    draft_store.save(draft)
    return draft


@router.post("/drafts/{draft_id}/schedule")
def schedule_draft(draft_id: str, body: ScheduleDraftRequest) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    if draft.status == DraftStatus.published:
        raise HTTPException(400, "Cannot schedule a draft that is already published")

    draft.scheduled_at = localize_to_utc(body.scheduled_at)
    draft.status = DraftStatus.approved
    draft_store.save(draft)
    return draft


@router.post("/drafts/{draft_id}/unschedule")
def unschedule_draft(draft_id: str) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    draft.scheduled_at = None
    draft_store.save(draft)
    return draft
