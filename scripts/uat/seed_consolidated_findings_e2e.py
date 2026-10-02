"""Only the guarded, owned Quote browser database; never the walkthrough."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.uat.seed_quote_communication_e2e import main as seed_base, _assert_owned_database
from scripts.uat.canonical_geography_fixture import ensure_canonical_geography
from backend import create_app
from backend.extensions import db
from backend.models import City, ExpertQuote, ShipmentRequest


def main():
    _assert_owned_database()
    seed_base()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        # The revision journey starts after an explicit synthetic customer response.
        discussion = fixture["journeys"]["discussion"]
        quoted = ExpertQuote.query.filter_by(public_id=discussion["quote_public_id"]).one()
        quoted.customer_response = "discussion"
        quoted.responded_at = datetime.now(timezone.utc)
        ensure_canonical_geography()
        origin = City.query.filter_by(geoname_id=1795855).one()
        other = City.query.filter_by(geoname_id=1796562).one()
        destination = City.query.filter_by(geoname_id=141681).one()
        fixture["handoff"] = []
        for label in ("exact", "variance"):
            req = ShipmentRequest(shipping_type="international", contact_phone="09123330000",
                tracking_code=f"CONSOLIDATED-{label}", origin_country_id=origin.country_id,
                origin_city_id=origin.id, dest_country_id=destination.country_id,
                dest_city_id=destination.id, status="won", status_request_status="new",
                assigned_to=fixture["expert_id"], customer_id=fixture["crm_customer_id"],
                operational_organization_id=fixture["organization_id"], ownership_scope="TENANT")
            db.session.add(req); db.session.flush()
            quote = ExpertQuote(shipment_request_id=req.id, amount=140000000,currency="IRR",
                created_by_expert_id=fixture["expert_id"], customer_response="accepted",
                responded_at=datetime.now(timezone.utc), operational_organization_id=fixture["organization_id"])
            db.session.add(quote); db.session.flush()
            fixture["handoff"].append({"request":req.public_id,"quote":quote.id,"tracking":req.tracking_code})
        fixture["geo"] = {"origin":origin.id,"other":other.id,"destination":destination.id,
            "country":origin.country_id,"parent":origin.province.geoname_id,"other_parent":other.province.geoname_id}
        db.session.commit()
    path.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")


if __name__ == "__main__":
    main()
