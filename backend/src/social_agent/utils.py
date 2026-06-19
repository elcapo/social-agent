from __future__ import annotations

from markdownify import markdownify as _md


def html_to_markdown(html: str) -> str:
    return _md(html, heading_style="ATX", bullets="-", strip=["script", "style"]).strip()
