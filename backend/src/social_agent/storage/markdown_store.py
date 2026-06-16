from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar

import frontmatter
import yaml

T = TypeVar("T")


def _default_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not serializable")


try:
    from enum import Enum
except ImportError:
    Enum = None


class MarkdownStore(Generic[T]):
    """Store that persists items as markdown files with YAML frontmatter."""

    def __init__(self, directory: Path, model_class: type[T], content_field: str = "content"):
        self.directory = Path(directory)
        self.model_class = model_class
        self.content_field = content_field
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, item_id: str) -> Path:
        return self.directory / f"{item_id}.md"

    def _serialize_frontmatter(self, data: dict) -> str:
        class Dumper(yaml.Dumper):
            pass

        Dumper.add_representer(datetime, lambda dumper, data: dumper.represent_str(data.isoformat()))

        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            Dumper=Dumper,
        )

    def save(self, item: T) -> Path:
        path = self._path_for(item.id)
        content = getattr(item, self.content_field, "")
        fm_data = item.to_frontmatter()
        body = content.strip() if content else ""

        fm = frontmatter.Post(body, **fm_data)
        with open(path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(fm))
        return path

    def get(self, item_id: str) -> Optional[T]:
        path = self._path_for(item_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        data = dict(post.metadata)
        data[self.content_field] = post.content.strip()
        return self.model_class.from_frontmatter(data)

    def list(self, filter_fn: Optional[Callable[[T], bool]] = None) -> list[T]:
        items: list[T] = []
        if not self.directory.exists():
            return items
        for path in sorted(self.directory.glob("*.md")):
            with open(path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            data = dict(post.metadata)
            data[self.content_field] = post.content.strip()
            item = self.model_class.from_frontmatter(data)
            if filter_fn is None or filter_fn(item):
                items.append(item)
        return items

    def delete(self, item_id: str) -> bool:
        path = self._path_for(item_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def count(self) -> int:
        if not self.directory.exists():
            return 0
        return len(list(self.directory.glob("*.md")))
