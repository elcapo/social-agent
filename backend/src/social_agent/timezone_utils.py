"""Helpers for converting between the configured local timezone and UTC.

Domain invariant: every persisted timestamp is timezone-aware UTC. These
helpers bridge user-facing naive datetimes — interpreted as the configured
local timezone (``settings.timezone``) — and that invariant.
"""
from __future__ import annotations

from datetime import datetime, timezone

from social_agent.config import get_tz


def localize_to_utc(dt: datetime) -> datetime:
    """Return a UTC-aware datetime.

    Naive datetimes are interpreted as the configured local timezone
    (``settings.timezone``) and converted to UTC. Aware datetimes are
    returned normalized to UTC (their original offset is respected).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_tz())
    return dt.astimezone(timezone.utc)


def to_local_iso(dt: datetime) -> str:
    """Return an ISO 8601 string in the configured local timezone.

    Naive datetimes are assumed to already be UTC (per the domain invariant)
    before conversion to the configured timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_tz()).isoformat()
