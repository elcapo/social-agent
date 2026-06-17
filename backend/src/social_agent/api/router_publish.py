from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from social_agent.models.draft import Draft, DraftStatus
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = Path("data")
draft_store = MarkdownStore[Draft](DATA_DIR / "drafts", Draft)

router = APIRouter(tags=["publish"])


@router.post("/publish/{draft_id}")
def publish_draft(draft_id: str) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    if draft.status != DraftStatus.approved:
        raise HTTPException(400, f"Draft is {draft.status.value}, only approved drafts can be published")

    draft.status = DraftStatus.published
    draft.published_at = datetime.now(timezone.utc)
    draft_store.save(draft)
    return draft
