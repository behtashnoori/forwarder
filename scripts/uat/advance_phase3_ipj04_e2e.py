"""Advance the owned IPJ-04 fixture after its real browser owner transfer.

The first browser chapter performs the owner-transfer Product command.  This
bounded synthetic setup then adds route-time bases and a report correction by
calling Product services, and establishes the documented ``completed``
precondition for the closure chapter.  It never creates transfer, correction,
ETA, or closure history directly.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import (
    CanonicalLocation,
    ExecutionUnit,
    OperationalEvent,
    OperationalShipment,
    RouteLeg,
    RoutePlan,
    utcnow,
)
from backend.owner_transfer_models import ShipmentOwnerTransfer
from backend.reported_fact_models import OperationalEventReportContext
from backend.services import reported_fact_service as reports
from backend.services import route_time_service as route_times


def _assert_owned_database() -> None:
    parsed = make_url(os.environ["DATABASE_URL"])
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("IPJ-04 setup requires APP_ENV=uat")
    if parsed.host != "127.0.0.1" or not (parsed.database or "").startswith(
        "forwarder_integrated_cert_p3_06_documents_p313_"
    ):
        raise RuntimeError("IPJ-04 setup is restricted to its owned loopback database")


def _location_reference(leg: RouteLeg, side: str) -> dict[str, int | str]:
    location_id = leg.origin_location_id if side == "origin" else leg.destination_location_id
    location = db.session.get(CanonicalLocation, location_id)
    if location is None:
        raise RuntimeError("IPJ-04 route location is missing")
    return {"source_type": location.source_type, "source_id": location.source_id}


def main() -> None:
    _assert_owned_database()
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).resolve()
    fixture = json.loads(manifest_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)

    with app.app_context():
        shipment = OperationalShipment.query.filter_by(
            public_id=fixture["p313_shipment"]
        ).one()
        new_owner = ExpertUser.query.filter_by(
            username="shared_transport_e2e_transfer_target"
        ).one()
        admin = ExpertUser.query.filter_by(
            username="shared_transport_e2e_admin"
        ).one()
        transfer = ShipmentOwnerTransfer.query.filter_by(
            operational_shipment_id=shipment.id
        ).one()
        if shipment.primary_responsible_expert_id != new_owner.id:
            raise RuntimeError("Browser owner transfer did not persist")
        if transfer.new_owner_id != new_owner.id:
            raise RuntimeError("Owner-transfer history does not match the current owner")

        plan = RoutePlan.query.filter_by(
            operational_shipment_id=shipment.id, is_active=True
        ).one()
        legs = RouteLeg.query.filter_by(route_plan_id=plan.id).order_by(
            RouteLeg.sequence_number, RouteLeg.id
        ).all()
        # Selection is a planning command.  The inherited fixture already has
        # an active route, so briefly expose its synthetic planning state,
        # execute the real commands, and return it to the same active state.
        plan.status = "draft"
        db.session.commit()
        selected_references: list[str] = []
        for leg in legs:
            version, _ = route_times.save(
                {"id": admin.id},
                {
                    "origin": _location_reference(leg, "origin"),
                    "destination": _location_reference(leg, "destination"),
                    "transport_mode": leg.transport_mode,
                    "movement_min_minutes": 60,
                    "movement_max_minutes": 120,
                    "stop_min_minutes": 0,
                    "stop_max_minutes": 30,
                    "effective_from": (leg.planned_departure - timedelta(days=2)).isoformat(),
                },
                str(uuid4()),
            )
            db.session.commit()
            leg = db.session.get(RouteLeg, leg.id)
            route_times.select_basis(
                shipment.public_id,
                plan.id,
                leg.id,
                {"id": new_owner.id},
                {
                    "expected_version": leg.version,
                    "expected_selection_revision": 0,
                    "reference_version_public_id": version.public_id,
                },
                str(uuid4()),
            )
            db.session.commit()
            selected_references.append(version.public_id)
        plan = db.session.get(RoutePlan, plan.id)
        plan.status = "active"
        db.session.commit()

        cargo = ShipmentCargoItem.query.filter_by(
            public_id=fixture["p305_cargo"]
        ).one()
        original = db.session.scalar(
            select(OperationalEventReportContext)
            .join(
                OperationalEvent,
                OperationalEvent.id
                == OperationalEventReportContext.operational_event_id,
            )
            .where(
                OperationalEventReportContext.operational_shipment_id == shipment.id,
                OperationalEvent.supersedes_event_id.is_(None),
            )
            .order_by(OperationalEvent.id)
            .limit(1)
        )
        if original is None or original.event.location_evidence is None:
            raise RuntimeError("Owned shared-Shipment report fixture is missing")
        correction, created = reports.create(
            shipment.public_id,
            {"id": new_owner.id},
            {
                "scope": original.scope,
                "target_public_id": db.session.get(
                    ExecutionUnit, original.execution_unit_id
                ).public_id
                if original.scope == "EXECUTION_UNIT"
                else cargo.public_id,
                "kind": "LOCATION",
                "source": "CARRIER_REPORT",
                "occurred_at": utcnow().isoformat(),
                "location": {
                    "canonical_location_public_id": db.session.get(
                        CanonicalLocation, legs[0].destination_location_id
                    ).public_id
                },
                "customer_message": "کالای شما از نقطه میانی عبور کرده است",
                "internal_note": "IPJ-04 owned synthetic correction",
                "impacted_cargo_public_ids": [cargo.public_id],
                "corrects_public_id": original.event.public_id,
                "reason": "اصلاح موقعیت برای گواه پیوستگی سفر",
            },
            str(uuid4()),
        )
        if not created:
            raise RuntimeError("IPJ-04 report correction was unexpectedly replayed")
        db.session.commit()

        # Completion is a documented starting-state prerequisite of the closure
        # command; no separate Product completion command exists in this slice.
        shipment = db.session.get(OperationalShipment, shipment.id)
        shipment.lifecycle_status = "completed"
        db.session.commit()
        fixture["p315_ipj04"] = {
            "shipment": shipment.public_id,
            "new_owner": new_owner.username,
            "original_report": original.event.public_id,
            "corrected_report": correction.event.public_id,
            "eta_cargo": cargo.public_id,
            "selected_route_time_versions": selected_references,
            "completed_precondition": "OWNED_SYNTHETIC_SETUP",
        }

    manifest_path.write_text(
        json.dumps(fixture, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    print("FWD_IPJ_04_MID_JOURNEY_SETUP=PASS")


if __name__ == "__main__":
    main()
