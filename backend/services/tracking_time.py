"""Server-owned M1 input resolution; never consult a browser or event location zone."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo

POLICY = "tracking.manual-iran.v1"
TEHRAN = ZoneInfo("Asia/Tehran")
WALL = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?\Z")
OFFSET = re.compile(r"(?P<wall>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?))(?P<basis>Z|[+-]\d{2}:\d{2})\Z")


class TrackingTimeError(ValueError):
    pass


def _wall(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 29 or not WALL.fullmatch(value):
        raise TrackingTimeError("time_input_wall must be a Gregorian ISO local date and time")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise TrackingTimeError("invalid local date or time") from exc
    if parsed.tzinfo is not None:
        raise TrackingTimeError("manual wall time must not carry an offset")
    return parsed


def manual(value: str, policy: str):
    if policy != POLICY:
        raise TrackingTimeError("tracking manual time policy is missing or invalid")
    wall = _wall(value)
    candidates = {
        wall.replace(tzinfo=TEHRAN, fold=fold).astimezone(timezone.utc)
        for fold in (0, 1)
        if wall.replace(tzinfo=TEHRAN, fold=fold).astimezone(timezone.utc)
        .astimezone(TEHRAN).replace(tzinfo=None) == wall
    }
    if len(candidates) != 1:
        raise TrackingTimeError("local Tehran time is ambiguous or nonexistent")
    return next(iter(candidates)), value, "Asia/Tehran", "manual", POLICY


def offset(value: str):
    if not isinstance(value, str):
        raise TrackingTimeError("occurred_at must carry an explicit numeric offset")
    match = OFFSET.fullmatch(value)
    if not match or len(match.group("wall")) > 29:
        raise TrackingTimeError("occurred_at must carry an explicit numeric offset")
    wall = _wall(match.group("wall"))
    basis = match.group("basis")
    if basis == "Z":
        basis = "+00:00"
    hours, minutes = int(basis[1:3]), int(basis[4:6])
    if minutes >= 60 or hours > 14 or (hours == 14 and minutes):
        raise TrackingTimeError("invalid UTC offset")
    delta = timedelta(hours=hours, minutes=minutes)
    if basis[0] == "-":
        delta = -delta
    instant = wall.replace(tzinfo=timezone(delta)).astimezone(timezone.utc)
    return instant, match.group("wall"), basis, "offset", None
