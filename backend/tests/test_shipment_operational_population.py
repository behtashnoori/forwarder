"""Freeze tests for Operational Shipment Population v1."""
from datetime import datetime, timedelta, timezone

import pytest

from backend.extensions import db
from backend.operational_models import OperationalShipment, RouteLeg, RoutePlan
from backend.services import operational_service
from backend.services.operational_service import OperationalError
from backend.services.shipment_population_service import (
    OperationalWindow,
    operational_shipment_population,
    parse_transport_datetime,
)
from backend.tests.test_operational_vertical_slice import (
    _auth,
    _direct_payload,
    _user,
    operational_app,
)


UTC = timezone.utc


def _shipment(app, key, start, end, *, legs=None):
    shipment, _ = operational_service.create_direct(
        _direct_payload(app, start, end), _user(app), key
    )
    shipment.public_id = f"00000000-0000-4000-8000-{key:0>12}"[-36:]
    plan = RoutePlan.query.filter_by(
        operational_shipment_id=shipment.id, is_active=True
    ).one()
    original = RouteLeg.query.filter_by(route_plan_id=plan.id).one()
    if legs:
        db.session.delete(original)
        db.session.flush()
        for sequence, departure, arrival in legs:
            db.session.add(RouteLeg(
                route_plan_id=plan.id,
                sequence_number=sequence,
                origin_location_id=app.config["phase1a"]["origin"],
                destination_location_id=app.config["phase1a"]["destination"],
                origin_snapshot=original.origin_snapshot,
                destination_snapshot=original.destination_snapshot,
                transport_mode="road",
                planned_departure=departure,
                planned_arrival=arrival,
            ))
    db.session.commit()
    return shipment


def _ids(app, *, start=None, end=None, status=None, limit=100, offset=0):
    statement = operational_shipment_population(
        _user(app), status=status, window=OperationalWindow(start, end)
    ).offset(offset).limit(limit)
    return [row.public_id for row in db.session.scalars(statement).all()]


def test_route_envelope_uses_first_and_last_sequence_not_timestamp_min_max(operational_app):
    base = datetime(2030, 1, 10, tzinfo=UTC)
    with operational_app.app_context():
        row = _shipment(operational_app, "1", base, base + timedelta(days=3), legs=[
            (1, base, base + timedelta(hours=2)),
            # Deliberately earlier timestamps on a later sequence.  Sequence is authority.
            (2, base - timedelta(days=10), base - timedelta(days=9)),
            (3, base + timedelta(days=2), base + timedelta(days=3)),
        ])
        assert row.public_id in _ids(
            operational_app,
            start=base + timedelta(days=1),
            end=base + timedelta(days=1, hours=1),
        )
        assert row.public_id not in _ids(
            operational_app,
            start=base - timedelta(days=9, hours=12),
            end=base - timedelta(days=9, hours=6),
        )


@pytest.mark.parametrize(
    "window_start,window_end,expected",
    [
        (-1, 4, True),   # envelope fully contained
        (1, 2, True),    # requested window inside envelope
        (-1, 1, True),   # lower overlap
        (2, 4, True),    # upper overlap
        (-1, 0, True),   # exact envelope start / requested end
        (3, 4, True),    # exact envelope end / requested start
        (4, 5, False),   # completely before requested window
        (-2, -1, False), # completely after requested window
    ],
)
def test_inclusive_route_envelope_overlap(operational_app, window_start, window_end, expected):
    base = datetime(2031, 1, 10, tzinfo=UTC)
    with operational_app.app_context():
        row = _shipment(operational_app, "2", base, base + timedelta(days=3))
        result = row.public_id in _ids(
            operational_app,
            start=base + timedelta(days=window_start),
            end=base + timedelta(days=window_end),
        )
        assert result is expected


def test_one_sided_windows_and_no_active_route_exclusion(operational_app):
    base = datetime(2032, 1, 10, tzinfo=UTC)
    with operational_app.app_context():
        row = _shipment(operational_app, "3", base, base + timedelta(days=2))
        assert row.public_id in _ids(operational_app, start=base + timedelta(days=2))
        assert row.public_id in _ids(operational_app, end=base)
        plan = RoutePlan.query.filter_by(operational_shipment_id=row.id, is_active=True).one()
        plan.is_active = False
        plan.status = "superseded"
        db.session.commit()
        assert row.public_id not in _ids(operational_app)


def test_timezone_normalization_and_naive_internal_rejection(operational_app):
    base = datetime(2033, 1, 10, 8, tzinfo=UTC)
    with operational_app.app_context():
        row = _shipment(operational_app, "4", base, base + timedelta(hours=8))
        utc_ids = _ids(operational_app, start=base, end=base + timedelta(hours=8))
        offset_window = OperationalWindow(
            datetime.fromisoformat("2033-01-10T11:30:00+03:30"),
            datetime.fromisoformat("2033-01-10T19:30:00+03:30"),
        )
        offset_ids = _ids(operational_app, start=offset_window.from_, end=offset_window.to)
        assert row.public_id in utc_ids and utc_ids == offset_ids
        assert offset_window.from_.tzinfo == UTC and offset_window.from_.hour == 8
        with pytest.raises(OperationalError, match="UTC offset"):
            OperationalWindow(datetime(2033, 1, 10), None)
        assert parse_transport_datetime("2033-01-10", "date_from").tzinfo == UTC


def test_status_governance_and_deterministic_public_identity_tie_breaker(operational_app):
    base = datetime(2034, 1, 10, tzinfo=UTC)
    with operational_app.app_context():
        second = _shipment(operational_app, "20", base, base + timedelta(hours=1))
        first = _shipment(operational_app, "10", base, base + timedelta(hours=1))
        shared = datetime(2030, 1, 1, tzinfo=UTC)
        first.created_at = second.created_at = shared
        db.session.commit()
        ordered = [item for item in _ids(operational_app) if item in {first.public_id, second.public_id}]
        assert ordered == sorted([first.public_id, second.public_id])
        with pytest.raises(OperationalError) as error:
            _ids(operational_app, status="sql:drop")
        assert error.value.code == "INVALID_SHIPMENT_STATUS"


def test_endpoint_and_reusable_authority_identity_order_equivalence(operational_app):
    base = datetime(2035, 1, 10, tzinfo=UTC)
    with operational_app.app_context():
        _shipment(operational_app, "31", base, base + timedelta(days=2))
        _shipment(operational_app, "32", base + timedelta(days=4), base + timedelta(days=5))
        expected = _ids(
            operational_app,
            start=base + timedelta(days=1),
            end=base + timedelta(days=3),
            limit=1,
        )
    response = operational_app.test_client().get(
        "/api/operational-shipments?date_from=2035-01-11T00:00:00Z&date_to=2035-01-13T00:00:00Z&per_page=1",
        headers=_auth(operational_app),
    )
    assert response.status_code == 200
    assert [row["public_id"] for row in response.json["data"]] == expected


def test_client_authority_spoof_is_ignored_and_assignment_precedes_pagination(operational_app):
    base = datetime(2036, 1, 10, tzinfo=UTC)
    with operational_app.app_context():
        visible = _shipment(operational_app, "41", base, base + timedelta(hours=1))
        hidden = _shipment(operational_app, "42", base, base + timedelta(hours=1))
        hidden.primary_responsible_expert_id = operational_app.config["phase1a"]["verifier"]
        hidden.created_at = visible.created_at + timedelta(days=1)
        db.session.commit()
        visible_public_id = visible.public_id
    response = operational_app.test_client().get(
        "/api/operational-shipments?per_page=1&organization_id=999&user_id=999",
        headers=_auth(operational_app),
    )
    assert response.status_code == 200
    assert [row["public_id"] for row in response.json["data"]] == [visible_public_id]
    assert response.json["meta"]["has_more"] is False
