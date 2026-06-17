from __future__ import annotations

from pathlib import Path
from typing import Optional

import frontmatter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from social_agent.agents.writer import WriterAgent
from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = Path("data")
draft_store = MarkdownStore[Draft](DATA_DIR / "drafts", Draft)
seed_store = MarkdownStore[Seed](DATA_DIR / "seeds", Seed)

router = APIRouter(tags=["drafts"])


class GenerateDraftsRequest(BaseModel):
    seed_id: str
    platforms: list[str]
    dry_run: bool = False


class GenerateDraftsResponse(BaseModel):
    drafts: list[Draft] | None = None
    raw_responses: dict[str, str] | None = None


class UpdateDraftRequest(BaseModel):
    status: Optional[str] = None
    content: Optional[str] = None
    notes: Optional[str] = None


@router.get("/drafts")
def list_drafts(platform: Optional[str] = None, status: Optional[str] = None) -> list[Draft]:
    def _filter(d: Draft) -> bool:
        if platform and d.platform != platform:
            return False
        if status and d.status.value != status:
            return False
        return True
    return draft_store.list(filter_fn=_filter)


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")
    return draft


@router.post("/drafts/generate", status_code=201)
def generate_drafts(body: GenerateDraftsRequest) -> GenerateDraftsResponse:
    seed = seed_store.get(body.seed_id)
    if not seed:
        raise HTTPException(404, f"Seed '{body.seed_id}' not found")

    if seed.status != SeedStatus.pending:
        raise HTTPException(400, f"Seed is {seed.status.value}, only pending seeds can be used")

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
            seed=seed,
            platform=p,
            platform_instructions=instructions,
            platform_name=platform_name,
            max_chars=max_chars,
            dry_run=body.dry_run,
        )

        if body.dry_run:
            raw_responses[p] = str(result)
        else:
            draft_store.save(result)
            drafts.append(result)

    if not body.dry_run:
        seed.status = SeedStatus.used
        seed_store.save(seed)

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

    draft_store.save(draft)
    return draft
