from backend.tests.test_operational_vertical_slice import operational_app, _user
from backend.tests.test_structured_route_progress_eta import _fixture
from backend.services import eta_service as eta
from backend.extensions import db
from backend.eta_models import CargoEtaSnapshot
from backend.tests.test_phase3_eta import occurrence


def test_known_pinned_basis_survives_unavailable_progress(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app, planned_distance_km="900.000")
        shipment, cargo = eta._scope(ctx["shipment"], ctx["cargo"], user=_user(operational_app))
        _, _, result, _ = eta.calculate(shipment, cargo)
        assert result["final"]["reason"] == "PROGRESS_UNDEFINED"
        assert result["route_context"]["legs"][0]["planned_distance_km"] == "900.000"
        assert result["planned_distance"] is None


def test_current_read_never_creates_or_replaces_a_saved_snapshot(operational_app):
    with operational_app.app_context():
        ctx = _fixture(operational_app, planned_distance_km="900.000")
        kwargs = {"user": _user(operational_app)}
        value = eta.current(ctx["shipment"], ctx["cargo"], **kwargs)
        assert value["snapshot"] is None and CargoEtaSnapshot.query.count() == 0
        old = eta.ensure_current_eta(ctx["shipment"], ctx["cargo"], **kwargs)
        db.session.commit()
        old_result = dict(old.result)
        occurrence(operational_app, ctx)
        value = eta.current(ctx["shipment"], ctx["cargo"], **kwargs)
        assert value["stale"] and value["snapshot"]["public_id"] == old.public_id
        assert CargoEtaSnapshot.query.count() == 1
        assert old.result == old_result
