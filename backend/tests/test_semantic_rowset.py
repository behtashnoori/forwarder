"""ROWSET v1 stays equivalent to the frozen Shipment population."""
from datetime import datetime, timedelta, timezone

import pytest

from backend.analytics import service as analytics
from backend.extensions import db
from backend.services import operational_service
from backend.services.operational_service import OperationalError
from backend.services.shipment_population_service import OperationalWindow, operational_shipment_population
from backend.tests.test_operational_vertical_slice import _direct_payload, _user, operational_app


def _rowset(**extra):
    return {"query_kind": "ROWSET", "semantic_version": "analytics-semantic-v2", "population": "SHIPMENTS", "columns": ["CUSTOMER", "ROUTE", "PLANNED_TIME", "OPEN_WORK_ITEMS", "SHIPMENT_STATUS"], "limit": 20, **extra}


def test_rowset_is_discriminated_bounded_and_population_equivalent(operational_app):
    base = datetime(2040, 1, 10, tzinfo=timezone.utc)
    with operational_app.app_context():
        first, _ = operational_service.create_direct(_direct_payload(operational_app, base, base + timedelta(days=2)), _user(operational_app), "rowset-1")
        second, _ = operational_service.create_direct(_direct_payload(operational_app, base + timedelta(days=4), base + timedelta(days=5)), _user(operational_app), "rowset-2")
        first_id, second_id = first.public_id, second.public_id
        expected = [row.public_id for row in db.session.scalars(operational_shipment_population(_user(operational_app), window=OperationalWindow(base + timedelta(days=1), base + timedelta(days=3))).limit(20)).all()]
        result = analytics.query(_rowset(operational_window={"from": (base + timedelta(days=1)).isoformat(), "to": (base + timedelta(days=3)).isoformat()}), _user(operational_app))
    assert result["result_kind"] == "ROWSET"
    assert [row["shipment_public_id"] for row in result["rows"]] == expected == [first_id]
    assert result["returned_row_count"] == 1
    assert set(result["rows"][0]) == {"shipment_public_id", "CUSTOMER", "ROUTE", "PLANNED_TIME", "OPEN_WORK_ITEMS", "SHIPMENT_STATUS"}
    assert second_id not in expected


@pytest.mark.parametrize("payload,code", [
    ({"columns": ["created_at"]}, "UNSUPPORTED_SEMANTIC_COLUMN"),
    ({"population": "SQL"}, "UNSUPPORTED_ROWSET_POPULATION"),
    ({"limit": 0}, "INVALID_LIMIT"),
    ({"sort": {"field": "id", "direction": "ASC"}}, "UNSUPPORTED_ROWSET_SORT"),
])
def test_rowset_rejects_raw_or_ungoverned_contracts(operational_app, payload, code):
    with operational_app.app_context(), pytest.raises(OperationalError) as error:
        analytics.query(_rowset(**payload), _user(operational_app))
    assert error.value.code == code


def test_legacy_aggregate_remains_aggregate(operational_app):
    with operational_app.app_context():
        result = analytics.query({"metrics": ["SHIPMENT_COUNT"]}, _user(operational_app))
    assert result["result_kind"] == "AGGREGATE"
