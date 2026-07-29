"""First-response SLA calculation for expert assignments."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Tehran"
DEFAULT_WORK_START = time(8, 0)
DEFAULT_WORK_END = time(18, 0)
# Current published company hours: Saturday-Wednesday 08:00-18:00,
# Thursday 08:00-16:00, Friday closed.
DEFAULT_WEEKLY_SCHEDULE = {
    0: (time(8, 0), time(18, 0)),
    1: (time(8, 0), time(18, 0)),
    2: (time(8, 0), time(18, 0)),
    3: (time(8, 0), time(16, 0)),
    5: (time(8, 0), time(18, 0)),
    6: (time(8, 0), time(18, 0)),
}
POLICY_VERSION = 1


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def calculate_working_deadline(
    start: datetime,
    working_minutes: int,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    work_start: time = DEFAULT_WORK_START,
    work_end: time = DEFAULT_WORK_END,
    weekly_schedule: dict[int, tuple[time, time]] | None = None,
    holidays: frozenset = frozenset(),
) -> datetime:
    """Return an aware UTC instant after consuming working minutes."""
    if not isinstance(working_minutes, int) or isinstance(working_minutes, bool):
        raise ValueError("working_minutes must be an integer")
    if not 1 <= working_minutes <= 10080:
        raise ValueError("working_minutes must be between 1 and 10080")
    schedule = weekly_schedule or DEFAULT_WEEKLY_SCHEDULE
    if any(day_start >= day_end for day_start, day_end in schedule.values()):
        raise ValueError("work_start must be earlier than work_end")

    zone = ZoneInfo(timezone_name)
    cursor = _as_utc(start).astimezone(zone)
    remaining = working_minutes
    while True:
        day = cursor.date()
        hours = schedule.get(cursor.weekday())
        is_working_day = hours is not None and day not in holidays
        selected_start, selected_end = hours or (work_start, work_end)
        day_start = datetime.combine(day, selected_start, zone)
        day_end = datetime.combine(day, selected_end, zone)
        if not is_working_day or cursor >= day_end:
            cursor = datetime.combine(day + timedelta(days=1), work_start, zone)
            continue
        if cursor < day_start:
            cursor = day_start
        available = int((day_end - cursor).total_seconds() // 60)
        if remaining <= available:
            return (cursor + timedelta(minutes=remaining)).astimezone(timezone.utc)
        remaining -= available
        cursor = datetime.combine(day + timedelta(days=1), work_start, zone)


def set_initial_assignment_sla(request_row, expert, *, assigned_at: datetime | None = None) -> bool:
    """Set SLA once; ordinary reassignment preserves the existing deadline."""
    if request_row.sla_due_at is not None:
        return False
    deadline = calculate_working_deadline(
        assigned_at or datetime.now(timezone.utc),
        expert.sla_response_work_minutes,
    )
    request_row.sla_due_at = deadline.replace(tzinfo=None)
    return True
