from datetime import datetime, timedelta, timezone

from backend.services.legacy_datetime import serialize_legacy_utc_datetime


def test_serialize_verified_legacy_utc_naive_without_shift():
    value = datetime(2026, 7, 25, 19, 1, 58, 519833)
    assert serialize_legacy_utc_datetime(value) == "2026-07-25T19:01:58.519833Z"


def test_serialize_utc_aware():
    value = datetime(2026, 7, 25, 19, 1, 58, 519833, tzinfo=timezone.utc)
    assert serialize_legacy_utc_datetime(value) == "2026-07-25T19:01:58.519833Z"


def test_serialize_offset_aware_to_same_instant():
    value = datetime(2026, 7, 25, 22, 31, 58, 519833, tzinfo=timezone(timedelta(hours=3, minutes=30)))
    assert serialize_legacy_utc_datetime(value) == "2026-07-25T19:01:58.519833Z"


def test_serialize_none():
    assert serialize_legacy_utc_datetime(None) is None
