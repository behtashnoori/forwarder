from datetime import date, datetime, timezone

import pytest

from backend.services.sla_service import calculate_working_deadline, set_initial_assignment_sla


def utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("start", "minutes", "expected"),
    [
        (utc(2026, 7, 27, 3, 30), 60, utc(2026, 7, 27, 5, 30)),
        (utc(2026, 7, 27, 4, 30), 60, utc(2026, 7, 27, 5, 30)),
        (utc(2026, 7, 27, 6, 30), 120, utc(2026, 7, 27, 8, 30)),
        (utc(2026, 7, 27, 14, 30), 60, utc(2026, 7, 28, 5, 30)),
        (utc(2026, 7, 27, 15, 0), 60, utc(2026, 7, 28, 5, 30)),
        (utc(2026, 7, 27, 4, 30), 30, utc(2026, 7, 27, 5, 0)),
        (utc(2026, 7, 27, 13, 30), 120, utc(2026, 7, 28, 5, 30)),
        (utc(2026, 7, 27, 13, 30), 720, utc(2026, 7, 29, 5, 30)),
        (utc(2026, 7, 30, 11, 30), 120, utc(2026, 8, 1, 5, 30)),
        (utc(2026, 7, 27, 4, 30), 660, utc(2026, 7, 28, 5, 30)),
        (utc(2026, 7, 26, 21, 0), 60, utc(2026, 7, 27, 5, 30)),
    ],
)
def test_published_work_schedule_boundaries(start, minutes, expected):
    assert calculate_working_deadline(start, minutes) == expected


def test_assignment_after_hours_starts_next_working_day():
    # Wednesday after closing -> Thursday at 08:00 Tehran.
    assert calculate_working_deadline(utc(2026, 7, 29, 15, 0), 60) == utc(
        2026, 7, 30, 5, 30
    )


def test_deadline_skips_friday_and_crosses_weekend_boundary():
    # Thursday 15:30 Tehran, 120 minutes => Saturday 09:30 Tehran.
    assert calculate_working_deadline(utc(2026, 7, 30, 12, 0), 120) == utc(
        2026, 8, 1, 6, 0
    )


def test_holiday_is_skipped():
    assert calculate_working_deadline(
        utc(2026, 7, 27, 4, 30),
        60,
        holidays=frozenset({date(2026, 7, 27)}),
    ) == utc(2026, 7, 28, 5, 30)


def test_aware_utc_input_is_preserved():
    assert calculate_working_deadline(utc(2026, 7, 27, 6, 30), 60) == utc(
        2026, 7, 27, 7, 30
    )


def test_naive_input_contract_is_utc():
    assert calculate_working_deadline(datetime(2026, 7, 27, 6, 30), 60) == utc(
        2026, 7, 27, 7, 30
    )


def test_reassignment_preserves_existing_deadline():
    class Request:
        sla_due_at = datetime(2026, 7, 27, 8, 30)

    class Expert:
        sla_response_work_minutes = 30

    row = Request()
    original = row.sla_due_at
    assert set_initial_assignment_sla(row, Expert(), assigned_at=utc(2026, 7, 27, 6)) is False
    assert row.sla_due_at == original


@pytest.mark.parametrize("value", [0, -1, 10081, True, 1.5])
def test_invalid_durations_are_rejected(value):
    with pytest.raises(ValueError):
        calculate_working_deadline(utc(2026, 7, 27, 6), value)
