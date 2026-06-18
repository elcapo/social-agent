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


def _normalize_mode(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA", "PA"):
        img = img.convert("RGB")
    elif img.mode == "CMYK":
        img = img.convert("RGB")
    elif img.mode == "P":
        img = img.convert("RGB")
    return img


def resize_if_needed(data: bytes, max_dim: int = 2048) -> bytes:
    img = Image.open(BytesIO(data))
    if max(img.size) <= max_dim and img.mode in ("RGB", "L"):
        return data
    img = _normalize_mode(img)
    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    buf = BytesIO()
    fmt = img.format or "PNG"
    if fmt == "JPG":
        fmt = "JPEG"
    exif = img.info.get("exif")
    save_kwargs: dict = {"format": fmt}
    if exif is not None:
        save_kwargs["exif"] = exif
    if fmt == "JPEG":
        save_kwargs["quality"] = 85
    img.save(buf, **save_kwargs)
    return buf.getvalue()


def prepare_media(source: str) -> bytes:
    if _is_url(source):
        data = download_image(source)
    else:
        data = read_local_image(source)
    validate_image(data)
    return resize_if_needed(data)
