from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from social_agent.config import settings
from social_agent.scheduler import ScheduledItemResult, run_once
from social_agent.storage import get_draft_repository

DATA_DIR = settings.data_dir.resolve()
draft_store = get_draft_repository()

router = APIRouter(tags=["scheduler"])


class SchedulerRunResponse(BaseModel):
    published: int
    failed: int
    results: list[ScheduledItemResult]


@router.post("/scheduler/run", response_model=SchedulerRunResponse)
def scheduler_run() -> SchedulerRunResponse:
    results = run_once(draft_store)
    return SchedulerRunResponse(
        published=sum(1 for r in results if r.success),
        failed=sum(1 for r in results if not r.success),
        results=results,
    )
