from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from social_agent.models.source import Source, SourcePriority, SourceType
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = Path("data")
source_store = MarkdownStore[Source](DATA_DIR / "sources", Source)

router = APIRouter(tags=["sources"])


@router.get("/sources")
def list_sources(source_type: Optional[str] = None) -> list[Source]:
    def _filter(s: Source) -> bool:
        if source_type and s.source_type.value != source_type:
            return False
        return True
    return source_store.list(filter_fn=_filter)


@router.post("/sources", status_code=201)
def create_source(
    name: str,
    source_type: SourceType,
    url: str,
    priority: SourcePriority = SourcePriority.medium,
    tags: list[str] = [],
) -> Source:
    source = Source(name=name, source_type=source_type, url=url, priority=priority, tags=tags)
    source_store.save(source)
    return source


@router.get("/sources/{source_id}")
def get_source(source_id: str) -> Source:
    source = source_store.get(source_id)
    if not source:
        raise HTTPException(404, f"Source '{source_id}' not found")
    return source


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str) -> None:
    if not source_store.delete(source_id):
        raise HTTPException(404, f"Source '{source_id}' not found")
