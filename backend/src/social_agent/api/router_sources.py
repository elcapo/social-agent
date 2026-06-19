from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from social_agent.config import settings
from social_agent.models.source import Source, SourcePriority, SourceType
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = settings.data_dir.resolve()
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
    tags: list[str] = Query([]),
    config: Optional[str] = Query(None),
) -> Source:
    parsed_config = json.loads(config) if config else {}
    source = Source(name=name, source_type=source_type, url=url, priority=priority, tags=tags, config=parsed_config)
    source_store.save(source)
    return source


@router.get("/sources/{source_id}")
def get_source(source_id: str) -> Source:
    source = source_store.get(source_id)
    if not source:
        raise HTTPException(404, f"Source '{source_id}' not found")
    return source


@router.patch("/sources/{source_id}")
def update_source(
    source_id: str,
    name: Optional[str] = None,
    source_type: Optional[SourceType] = None,
    url: Optional[str] = None,
    priority: Optional[SourcePriority] = None,
    tags: Optional[list[str]] = Query(None),
    config: Optional[str] = Query(None),
    enabled: Optional[bool] = None,
) -> Source:
    source = source_store.get(source_id)
    if not source:
        raise HTTPException(404, f"Source '{source_id}' not found")

    if name is not None:
        source.name = name
    if source_type is not None:
        source.source_type = source_type
    if url is not None:
        source.url = url
    if priority is not None:
        source.priority = priority
    if tags is not None:
        source.tags = tags
    if config is not None:
        source.config = json.loads(config)
    if enabled is not None:
        source.enabled = enabled

    source_store.save(source)
    return source


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str) -> None:
    if not source_store.delete(source_id):
        raise HTTPException(404, f"Source '{source_id}' not found")
