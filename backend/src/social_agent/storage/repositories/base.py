"""Generic repository `Protocol` mirroring the `MarkdownStore` API surface.

`Repository[T]` declares the CRUD operations every persistence backend must
expose: `save`, `get`, `list`, `delete`, `count`. Specific entity repositories
extend this with extra query methods (see the sibling modules).

Using `Protocol` (structural typing) means `MarkdownStore` satisfies the
interface without inheriting from it — keeping the Markdown backend working
unchanged.
"""

from __future__ import annotations

from typing import Callable, Optional, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class Repository(Protocol[T]):
    """Generic CRUD repository over items of type ``T``."""

    def save(self, item: T) -> object:
        """Persist ``item`` and return a handle (path, row id, etc.)."""
        ...

    def get(self, item_id: str) -> Optional[T]:
        """Return the item with id ``item_id`` or ``None`` if not found."""
        ...

    def list(self, filter_fn: Optional[Callable[[T], bool]] = None) -> list[T]:
        """Return all items, optionally filtered by ``filter_fn``."""
        ...

    def delete(self, item_id: str) -> bool:
        """Delete the item with id ``item_id``. Return ``True`` if it existed."""
        ...

    def count(self) -> int:
        """Return the total number of stored items."""
        ...
