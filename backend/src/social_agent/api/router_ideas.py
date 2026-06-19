from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from social_agent.agents.ideator import IdeatorAgent
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = Path("data")
idea_store = MarkdownStore[Idea](DATA_DIR / "ideas", Idea)
seed_store = MarkdownStore[Seed](DATA_DIR / "seeds", Seed)

router = APIRouter(tags=["ideas"])


class GenerateIdeaRequest(BaseModel):
    seed_id: str
    interests: str
    dry_run: bool = False


class GenerateIdeaResponse(BaseModel):
    idea: Idea | None = None
    raw_response: str | None = None


class UpdateIdeaRequest(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None


@router.get("/ideas")
def list_ideas(status: Optional[str] = None) -> list[Idea]:
    def _filter(i: Idea) -> bool:
        if status and i.status.value != status:
            return False
        return True
    items = idea_store.list(filter_fn=_filter)
    items.sort(key=lambda i: i.created_at or "", reverse=True)
    return items


@router.get("/ideas/{idea_id}")
def get_idea(idea_id: str) -> Idea:
    idea = idea_store.get(idea_id)
    if not idea:
        raise HTTPException(404, f"Idea '{idea_id}' not found")
    return idea


@router.post("/ideas/generate", status_code=201)
def generate_idea(body: GenerateIdeaRequest) -> GenerateIdeaResponse:
    seed = seed_store.get(body.seed_id)
    if not seed:
        raise HTTPException(404, f"Seed '{body.seed_id}' not found")

    if seed.status != SeedStatus.approved:
        raise HTTPException(
            400,
            f"Seed is {seed.status.value}, only approved seeds can generate ideas",
        )

    ideator = IdeatorAgent()
    result = ideator.generate_idea(seed, body.interests, dry_run=body.dry_run)

    if body.dry_run:
        return GenerateIdeaResponse(raw_response=str(result))

    if result is None:
        raise HTTPException(500, "Ideator returned an invalid response")

    idea_store.save(result)

    seed.status = SeedStatus.used
    seed_store.save(seed)

    return GenerateIdeaResponse(idea=result)


@router.patch("/ideas/{idea_id}")
def update_idea(idea_id: str, body: UpdateIdeaRequest) -> Idea:
    idea = idea_store.get(idea_id)
    if not idea:
        raise HTTPException(404, f"Idea '{idea_id}' not found")

    if body.status:
        idea.status = IdeaStatus(body.status)
    if body.title is not None:
        idea.title = body.title
    if body.summary is not None:
        idea.summary = body.summary

    idea_store.save(idea)
    return idea


@router.delete("/ideas/{idea_id}", status_code=204)
def delete_idea(idea_id: str) -> None:
    idea = idea_store.get(idea_id)
    if not idea:
        raise HTTPException(404, f"Idea '{idea_id}' not found")
    idea_store.delete(idea_id)
