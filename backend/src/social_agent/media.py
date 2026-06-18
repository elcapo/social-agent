from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image

MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_FORMATS = {"PNG", "JPEG", "GIF", "WEBP"}


def _is_url(path: str) -> bool:
    return urlparse(path).scheme in ("http", "https")


def _resolve_path(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return Path.cwd() / p


def validate_image(data: bytes) -> Image.Image:
    img = Image.open(BytesIO(data))
    if img.format not in ALLOWED_FORMATS:
        raise ValueError(f"Unsupported image format: {img.format}. Allowed: {', '.join(sorted(ALLOWED_FORMATS))}")
    if len(data) > MAX_IMAGE_SIZE:
        raise ValueError(f"Image too large: {len(data)} bytes (max {MAX_IMAGE_SIZE})")
    return img


def download_image(url: str) -> bytes:
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    return resp.content


def read_local_image(path: str) -> bytes:
    p = _resolve_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image file not found: {path} (resolved: {p})")
    return p.read_bytes()


def resize_if_needed(data: bytes, max_dim: int = 2048) -> bytes:
    img = Image.open(BytesIO(data))
    if max(img.size) <= max_dim:
        return data
    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    buf = BytesIO()
    fmt = img.format or "PNG"
    img.save(buf, format=fmt)
    return buf.getvalue()


def prepare_media(source: str) -> bytes:
    if _is_url(source):
        data = download_image(source)
    else:
        data = read_local_image(source)
    validate_image(data)
    return resize_if_needed(data)
