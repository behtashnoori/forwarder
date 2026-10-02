"""PostgreSQL 18 proof for atomic Shipment/Cargo/route creation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.cargo_models import CargoCatalogItem, ShipmentCargoItem
from backend.extensions import db
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.models import (
    City, Country,
    CargoType,
    Customer,
    ExpertQuote,
    ExpertUser,
    Province,
    RequestCargoItem,
    ShipmentRequest,
    UnitOfMeasure,
)
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    RouteCargoDestination,
    RouteLeg,
    RoutePlan,
)
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from backend.services import operational_service


URL = os.environ.get("SHIPMENT_CARGO_CREATION_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(
    not URL, reason="requires explicit owned SHIPMENT_CARGO_CREATION_POSTGRES_URL"
)


def test_postgresql18_atomic_lineage_route_and_concurrent_creation():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_cargo_create_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(
            connection.execute(sa.text("SHOW server_version_num")).scalar_one()
        ) < 190000
    config = alembic_config(URL)
    prepare_version_table_for_upgrade(URL, config)
    command.upgrade(config, "head")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": URL,
            "SECRET_KEY": "shipment-cargo-create-postgresql",
        },
        skip_startup=True,
    )
    with app.app_context():
        org = OperationalOrganization(name="Cargo Creation PG Org")
        expert = ExpertUser(
            username="cargo-create-pg-expert",
            password_hash="unused",
            full_name="Cargo Creation Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        db.session.add_all([org, expert])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=org.id,
                user_id=expert.id,
                permissions=[
                    "operational_shipment.read", "request.read",
                    "operational_shipment.create",
                ],
            )
        )
        origin = Province(name_fa="مبدأ", code="CCPG-O")
        destination = Province(name_fa="مقصد", code="CCPG-D")
        customer = Customer(
            first_name="Cargo",
            last_name="Customer",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        cargo_type = CargoType(
            immutable_code="CCPG_ENGINE_PARTS",
            fa_name="قطعات موتور",
            en_name="Engine parts",
            is_active=True,
        )
        uom = UnitOfMeasure(
            immutable_code="CCPG_PIECE",
            fa_name="عدد",
            en_name="Piece",
            symbol="pcs",
            measurement_dimension="COUNT",
            is_active=True,
        )
        db.session.add_all([origin, destination, customer, cargo_type, uom])
        db.session.flush()
        db.session.add_all(
            [
                OrganizationCargoTypeActivation(
                    organization_id=org.id,
                    cargo_type_id=cargo_type.id,
                    status="ACTIVE",
                    created_by=expert.id,
                    updated_by=expert.id,
                ),
                OrganizationUnitOfMeasureActivation(
                    organization_id=org.id,
                    unit_of_measure_id=uom.id,
                    status="ACTIVE",
                    created_by=expert.id,
                    updated_by=expert.id,
                ),
            ]
        )
        request_row = ShipmentRequest(
            contact_phone="09000000009",
            assigned_to=expert.id,
            customer_id=customer.id,
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        db.session.add(request_row)
        db.session.flush()
        # Exact Request identity is reused, not looked up by its display name.
        cn = Country(code="CN",name_fa="چین",name_en="China",is_active=True)
        db.session.add(cn); db.session.flush()
        origin.country_id = cn.id
        requested_city = City(name_fa="شاوشنگ",name_en="Shaoxing",geoname_id=1795855,
            province_id=origin.id,country_id=cn.id,is_active=True)
        other_city = City(name_fa="Sanxing",name_en="Sanxing",geoname_id=1796562,
            province_id=origin.id,country_id=cn.id,is_active=True)
        db.session.add_all([requested_city,other_city]); db.session.flush()
        request_row.origin_city_id = requested_city.id
        request_row.origin_country_id = cn.id
        request_cargo = RequestCargoItem(
            shipment_request_id=request_row.id,
            position=1,
            cargo_type=cargo_type,
            description="Requested engine parts",
            quantity=Decimal("100"),
            uom=uom,
        )
        catalog = CargoCatalogItem(
            organization_id=org.id,
            immutable_code="CCPG_XU7P",
            fa_name="مجموعه قطعات موتور XU7P",
            en_name="XU7P engine parts",
            cargo_type=cargo_type,
            default_uom=uom,
            search_text="xu7p",
            created_by=expert.id,
            updated_by=expert.id,
        )
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            amount=1000,
            currency="IRR",
            created_by_expert_id=expert.id,
            created_at=datetime.now(timezone.utc),
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=org.id,
        )
        db.session.add_all([request_cargo, catalog, quote])
        db.session.commit()
        ids = {
            "expert": expert.id,
            "quote": quote.id,
            "request": request_row.id,
            "request_cargo": request_cargo.public_id,
            "catalog": catalog.public_id,
            "origin": requested_city.id,
            "other_city": other_city.id,
            "customer": customer.id,
            "org": org.id,
            "destination": destination.id,
        }

    departure = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "accepted_quote_id": ids["quote"],
        "planned_departure": departure.isoformat(),
        "planned_arrival": (departure + timedelta(hours=5)).isoformat(),
        "origin": {"source_type": "city", "source_id": ids["origin"]},
        "destination": {
            "source_type": "province",
            "source_id": ids["destination"],
        },
        "transport_mode": "road",
        "cargo_items": [
            {
                "source_request_cargo_item_public_id": ids["request_cargo"],
                "catalog_item_public_id": ids["catalog"],
                "planned_quantity": "100",
            }
        ],
    }

    def create(key: str):
        with app.app_context():
            try:
                row, created = operational_service.create_from_accepted_quote(
                    payload, {"id": ids["expert"]}, key
                )
                return row.id, created
            except operational_service.OperationalError as exc:
                db.session.rollback()
                return exc.code, False
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(create, ("cargo-create-a", "cargo-create-b")))
    assert sum(isinstance(identity, int) for identity, _created in outcomes) == 1
    assert sum(identity == "OPERATIONAL_SHIPMENT_ALREADY_EXISTS" for identity, _ in outcomes) == 1

    with app.app_context():
        shipment = OperationalShipment.query.filter_by(
            accepted_quote_id=ids["quote"]
        ).one()
        cargo = ShipmentCargoItem.query.filter_by(
            operational_shipment_id=shipment.id
        ).one()
        plan = RoutePlan.query.filter_by(
            operational_shipment_id=shipment.id, is_active=True
        ).one()
        leg = RouteLeg.query.filter_by(route_plan_id=plan.id).one()
        mapping = RouteCargoDestination.query.filter_by(
            operational_shipment_id=shipment.id,
            route_plan_id=plan.id,
            shipment_cargo_item_id=cargo.id,
        ).one()
        assert cargo.source_shipment_request_id == ids["request"]
        assert cargo.source_request_cargo_item.public_id == ids["request_cargo"]
        assert cargo.catalog_item.public_id == ids["catalog"]
        assert cargo.requested_quantity == Decimal("100")
        assert cargo.planned_quantity == Decimal("100")
        assert cargo.actual_quantity is None
        assert cargo.uom.fa_name == "عدد"
        assert mapping.destination_route_leg_id == leg.id
        from backend.services.request_endpoint_projection import endpoints
        request_row = db.session.get(ShipmentRequest, ids["request"])
        assert endpoints(request_row)["origin"]["reference"]["source_id"] == ids["origin"]
        assert leg.origin_snapshot["canonical_reference"] == {"source_type":"city","source_id":ids["origin"]}
        from backend.services.operational_projection_service import _identity
        assert _identity(shipment, {}, {"id":ids["expert"]})["requested_endpoints"]["origin"]["reference"]["source_id"] == ids["origin"]
        assert ShipmentCargoItem.query.count() == 1
        assert RouteCargoDestination.query.count() == 1
        # A deliberate operational difference remains permitted and does not rewrite demand.
        second = ShipmentRequest(contact_phone="09120000000",shipping_type="domestic",status="won",
            status_request_status="new",assigned_to=ids["expert"],customer_id=ids["customer"],
            ownership_scope="TENANT",operational_organization_id=ids["org"],origin_city_id=ids["origin"])
        db.session.add(second); db.session.flush()
        q = ExpertQuote(shipment_request_id=second.id,amount=140000000,currency="IRR",
            created_by_expert_id=ids["expert"],customer_response="accepted",operational_organization_id=ids["org"])
        db.session.add(q); db.session.commit()
        changed = {**payload,"accepted_quote_id":q.id,"origin":{"source_type":"city","source_id":ids["other_city"]}}
        changed.pop("cargo_items")
        different, _ = operational_service.create_from_accepted_quote(changed,{"id":ids["expert"]},"explicit-different-origin")
        different_plan = RoutePlan.query.filter_by(operational_shipment_id=different.id,is_active=True).one()
        different_leg = RouteLeg.query.filter_by(route_plan_id=different_plan.id).one()
        assert different_leg.origin_snapshot["canonical_reference"]["source_id"] == ids["other_city"]
        assert db.session.get(ShipmentRequest,second.id).origin_city_id == ids["origin"]
    engine.dispose()
