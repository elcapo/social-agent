"""Repository pattern interfaces for the social_agent persistence layer.

Each repository is a `typing.Protocol` (structural typing), so any class that
implements the right method signatures satisfies the interface — including the
existing `MarkdownStore` (via duck typing) and the new SQLAlchemy
implementations. This avoids forcing a common base class and keeps the
Markdown backend working unchanged.
"""

from __future__ import annotations

from .base import Repository
from .draft_repository import DraftRepository
from .idea_repository import IdeaRepository
from .seed_repository import SeedRepository
from .source_repository import SourceRepository

__all__ = [
    "Repository",
    "SourceRepository",
    "SeedRepository",
    "IdeaRepository",
    "DraftRepository",
]
