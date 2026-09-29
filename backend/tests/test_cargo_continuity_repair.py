"""Focused qualification for the governed historical Cargo continuity repair."""

from datetime import datetime, timezone
from decimal import Decimal
import json

from alembic import command
import pytest
from sqlalchemy.engine import make_url

from backend import cargo_continuity_repair_cli as repair_cli
from backend import create_app
from backend.cargo_models import ExecutionUnitCargoAllocation, ShipmentCargoItem
from backend.delivery_models import CargoDelivery
from backend.extensions import db
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.models import (
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
    CanonicalLocation,
    OperationalAudit,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOrganization,
    OperationalOutbox,
    OperationalShipment,
    RouteCargoDestination,
    RouteLeg,
    RoutePlan,
    RouteStageExecution,
    ExecutionUnit,
)
from backend.services.cargo_continuity_repair_service import (
    IDEMPOTENCY_OPERATION,
    REPAIR_ACTION,
    CargoContinuityRepairError,
    apply_repair,
    plan_repair,
)


TRACKING_CODE = "FWD-REQ-0-CONTINUITY"
ADMIN_USERNAME = "continuity-platform-admin"
FOREIGN_ADMIN_USERNAME = "continuity-foreign-platform-admin"
EXPERT_USERNAME = "continuity-expert"


@pytest.fixture()
def repair_app(request):
    database_url = getattr(request, "param", "sqlite:///:memory:")
    use_model_schema = make_url(database_url).get_backend_name() == "sqlite"
    if not use_model_schema:
        config = alembic_config(database_url)
        prepare_version_table_for_upgrade(database_url, config)
        command.upgrade(config, "head")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_url,
            "SECRET_KEY": "cargo-continuity-repair-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        if use_model_schema:
            db.create_all()
        org = OperationalOrganization(name="Continuity Repair Org", is_active=True)
        foreign_org = OperationalOrganization(name="Foreign Repair Org", is_active=True)
        creator = ExpertUser(
            username=EXPERT_USERNAME,
            password_hash="unused",
            full_name="Owning Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        admin = ExpertUser(
            username=ADMIN_USERNAME,
            password_hash="unused",
            full_name="System Maintenance Admin",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        foreign_admin = ExpertUser(
            username=FOREIGN_ADMIN_USERNAME,
            password_hash="unused",
            full_name="Foreign System Maintenance Admin",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        db.session.add_all([org, foreign_org, creator, admin, foreign_admin])
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id,
                    user_id=creator.id,
                    permissions=["operational_shipment.read"],
                ),
                OperationalMembership(
                    organization_id=org.id,
                    user_id=admin.id,
                    permissions=[],
                ),
                OperationalMembership(
                    organization_id=foreign_org.id,
                    user_id=foreign_admin.id,
                    permissions=[],
                ),
            ]
        )
        origin_province = Province(name_fa="تهران", code="CCR-O")
        destination_province = Province(name_fa="بندرعباس", code="CCR-D")
        branch_a_province = Province(name_fa="شیراز", code="CCR-A")
        branch_b_province = Province(name_fa="یزد", code="CCR-B")
        customer = Customer(
            first_name="Cargo",
            last_name="Owner",
            phone="09120000991",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=org.id,
        )
        cargo_type = CargoType(
            immutable_code="CCR_ENGINE_PARTS",
            fa_name="قطعات موتور",
            en_name="Engine parts",
            is_active=True,
        )
        uom = UnitOfMeasure(
            immutable_code="CCR_PIECE",
            fa_name="عدد",
            en_name="Piece",
            symbol="pcs",
            measurement_dimension="COUNT",
            is_active=True,
        )
        db.session.add_all(
            [
                origin_province,
                destination_province,
                branch_a_province,
                branch_b_province,
                customer,
                cargo_type,
                uom,
            ]
        )
        db.session.flush()
        request_row = ShipmentRequest(
            contact_phone="09120000991",
            tracking_code=TRACKING_CODE,
            shipping_type="domestic",
            origin_province_id=origin_province.id,
            dest_province_id=destination_province.id,
            assigned_to=creator.id,
            customer_id=customer.id,
            operational_organization_id=org.id,
            ownership_scope="TENANT",
        )
        db.session.add(request_row)
        db.session.flush()
        source_cargo = RequestCargoItem(
            shipment_request_id=request_row.id,
            position=1,
            cargo_type=cargo_type,
            description="Requested engine parts",
            quantity=Decimal("100"),
            uom=uom,
        )
        quote = ExpertQuote(
            shipment_request_id=request_row.id,
            amount=1000,
            currency="IRR",
            created_by_expert_id=creator.id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            customer_response="accepted",
            responded_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            operational_organization_id=org.id,
        )
        db.session.add_all([source_cargo, quote])
        db.session.flush()
        shipment = OperationalShipment(
            organization_id=org.id,
            source_type="accepted_quote",
            customer_id=customer.id,
            shipment_request_id=request_row.id,
            accepted_quote_id=quote.id,
            lifecycle_status="planned",
            created_by_user_id=creator.id,
            primary_responsible_expert_id=creator.id,
        )
        db.session.add(shipment)
        db.session.flush()
        route_plan = RoutePlan(
            operational_shipment_id=shipment.id,
            revision=1,
            status="active",
            is_active=True,
            created_by_user_id=creator.id,
        )
        origin = CanonicalLocation(
            source_type="province",
            source_id=origin_province.id,
            location_type="province",
            display_name=origin_province.name_fa,
            country_code="IR",
        )
        destination = CanonicalLocation(
            source_type="province",
            source_id=destination_province.id,
            location_type="province",
            display_name=destination_province.name_fa,
            country_code="IR",
        )
        branch_a = CanonicalLocation(
            source_type="province",
            source_id=branch_a_province.id,
            location_type="province",
            display_name=branch_a_province.name_fa,
            country_code="IR",
        )
        branch_b = CanonicalLocation(
            source_type="province",
            source_id=branch_b_province.id,
            location_type="province",
            display_name=branch_b_province.name_fa,
            country_code="IR",
        )
        db.session.add_all([route_plan, origin, destination, branch_a, branch_b])
        db.session.flush()
        route_leg = RouteLeg(
            route_plan_id=route_plan.id,
            sequence_number=1,
            origin_location_id=origin.id,
            destination_location_id=destination.id,
            origin_snapshot={"display_name": origin.display_name},
            destination_snapshot={"display_name": destination.display_name},
            transport_mode="road",
            status="planned",
        )
        preserved_updated_at = datetime(2025, 5, 4, 3, 2, 1, tzinfo=timezone.utc)
        cargo = ShipmentCargoItem(
            operational_shipment_id=shipment.id,
            cargo_owner_customer_id=customer.id,
            line_number=1,
            cargo_type=cargo_type,
            quantity=Decimal("100"),
            planned_quantity=Decimal("100"),
            uom=uom,
            display_name_snapshot="Requested engine parts",
            cargo_type_code_snapshot=cargo_type.immutable_code,
            cargo_type_fa_snapshot=cargo_type.fa_name,
            cargo_type_en_snapshot=cargo_type.en_name,
            uom_code_snapshot=uom.immutable_code,
            uom_symbol_snapshot=uom.symbol,
            created_by=creator.id,
            updated_by=creator.id,
            updated_at=preserved_updated_at,
        )
        db.session.add_all([route_leg, cargo])
        db.session.flush()
        db.session.add(
            OperationalAudit(
                organization_id=org.id,
                actor_user_id=creator.id,
                action="SHIPMENT_CARGO_CREATED",
                entity_type="ShipmentCargoItem",
                entity_id=cargo.id,
                metadata_json={
                    "cargo_public_id": cargo.public_id,
                    "shipment_public_id": shipment.public_id,
                    "version": 1,
                    "changed_fields": [
                        "source_request_public_id",
                        "source_request_cargo_item_public_id",
                        "requested_quantity",
                    ],
                    "changes": {
                        "source_request_public_id": {"before": None, "after": None},
                        "source_request_cargo_item_public_id": {
                            "before": None,
                            "after": None,
                        },
                        "requested_quantity": {"before": None, "after": None},
                    },
                },
            )
        )
        db.session.add_all(
            [
                OperationalAudit(
                    organization_id=org.id,
                    actor_user_id=creator.id,
                    action="operational_shipment.created",
                    entity_type="OperationalShipment",
                    entity_id=shipment.id,
                    metadata_json={
                        "shipment_public_id": shipment.public_id,
                        "source_type": "accepted_quote",
                        "customer_id": customer.id,
                        "idempotency_key": "continuity-create",
                    },
                ),
                OperationalIdempotency(
                    organization_id=org.id,
                    operation="create_shipment",
                    resource_type="accepted_quote",
                    command_resource_id=quote.id,
                    idempotency_key="continuity-create",
                    request_hash="c" * 64,
                    result_resource_id=shipment.id,
                ),
            ]
        )
        db.session.commit()
        context = {
            "org_id": org.id,
            "creator_id": creator.id,
            "admin_id": admin.id,
            "shipment_id": shipment.id,
            "shipment_public_id": shipment.public_id,
            "request_id": request_row.id,
            "source_cargo_id": source_cargo.id,
            "source_cargo_public_id": source_cargo.public_id,
            "cargo_id": cargo.id,
            "cargo_public_id": cargo.public_id,
            "cargo_type_id": cargo_type.id,
            "uom_id": uom.id,
            "customer_id": customer.id,
            "plan_id": route_plan.id,
            "leg_id": route_leg.id,
            "destination_id": destination.id,
            "branch_a_id": branch_a.id,
            "branch_b_id": branch_b.id,
            "preserved_updated_at": preserved_updated_at,
        }
        yield app, context
        db.session.remove()
        if use_model_schema:
            db.drop_all()


def _plan(ctx, *, actor=ADMIN_USERNAME, tracking_code=TRACKING_CODE):
    return plan_repair(
        ctx["shipment_public_id"],
        actor,
        tracking_code,
        ctx["cargo_public_id"],
        ctx["source_cargo_public_id"],
        ctx["plan_id"],
        ctx["leg_id"],
    )


def _apply(ctx, fingerprint, *, actor=ADMIN_USERNAME, tracking_code=TRACKING_CODE):
    return apply_repair(
        ctx["shipment_public_id"],
        actor,
        approval_reference="ADR-072/operator-review-1",
        expected_plan_fingerprint=fingerprint,
        operator=actor,
        expected_request_tracking_code=tracking_code,
        expected_cargo_public_id=ctx["cargo_public_id"],
        expected_source_request_cargo_public_id=ctx["source_cargo_public_id"],
        expected_route_plan_id=ctx["plan_id"],
        expected_terminal_route_leg_id=ctx["leg_id"],
    )


def _conflict_codes(result):
    return {item["code"] for item in result["conflicts"]}


def _cli_binding_args(ctx):
    return [
        "--expected-cargo-public-id",
        ctx["cargo_public_id"],
        "--expected-source-request-cargo-public-id",
        ctx["source_cargo_public_id"],
        "--expected-route-plan-id",
        str(ctx["plan_id"]),
        "--expected-terminal-route-leg-id",
        str(ctx["leg_id"]),
    ]


def _repair_counts(ctx):
    return {
        "mapping": db.session.scalar(
            db.select(db.func.count())
            .select_from(RouteCargoDestination)
            .where(RouteCargoDestination.shipment_cargo_item_id == ctx["cargo_id"])
        ),
        "audit": db.session.scalar(
            db.select(db.func.count())
            .select_from(OperationalAudit)
            .where(
                OperationalAudit.entity_type == "ShipmentCargoItem",
                OperationalAudit.entity_id == ctx["cargo_id"],
                OperationalAudit.action == REPAIR_ACTION,
            )
        ),
        "outbox": db.session.scalar(
            db.select(db.func.count())
            .select_from(OperationalOutbox)
            .where(
                OperationalOutbox.aggregate_type == "ShipmentCargoItem",
                OperationalOutbox.aggregate_id == ctx["cargo_id"],
                OperationalOutbox.event_type == "cargo_continuity.repaired",
            )
        ),
        "idempotency": db.session.scalar(
            db.select(db.func.count())
            .select_from(OperationalIdempotency)
            .where(
                OperationalIdempotency.operation == IDEMPOTENCY_OPERATION,
                OperationalIdempotency.command_resource_id == ctx["shipment_id"],
            )
        ),
    }


def test_a_k_eligible_plan_is_read_only_and_requires_exact_reviewed_request(repair_app):
    _app, ctx = repair_app
    cargo = db.session.get(ShipmentCargoItem, ctx["cargo_id"])
    before = (
        cargo.source_shipment_request_id,
        cargo.source_request_cargo_item_id,
        cargo.requested_quantity,
        cargo.version,
        cargo.updated_at,
        _repair_counts(ctx),
    )

    result = _plan(ctx)

    db.session.expire_all()
    cargo = db.session.get(ShipmentCargoItem, ctx["cargo_id"])
    assert result["eligibility"] == "YES"
    assert result["state"] == "MISSING_CONTINUITY"
    assert result["proposed"]["source_request_tracking_code"] == TRACKING_CODE
    assert len(result["plan_fingerprint"]) == 64
    assert (
        cargo.source_shipment_request_id,
        cargo.source_request_cargo_item_id,
        cargo.requested_quantity,
        cargo.version,
        cargo.updated_at,
        _repair_counts(ctx),
    ) == before

    mismatch = _plan(ctx, tracking_code=TRACKING_CODE.replace("0", "O"))
    assert mismatch["eligibility"] == "NO"
    assert "EXPECTED_SOURCE_REQUEST_MISMATCH" in _conflict_codes(mismatch)


def test_b_ambiguous_source_request_cargo_refuses_repair(repair_app):
    _app, ctx = repair_app
    db.session.add(
        RequestCargoItem(
            shipment_request_id=ctx["request_id"],
            position=2,
            cargo_type_id=ctx["cargo_type_id"],
            description="Second possible source",
            quantity=Decimal("100"),
            uom_id=ctx["uom_id"],
        )
    )
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "SOURCE_REQUEST_CARGO_AMBIGUOUS" in _conflict_codes(result)


def test_c_multiple_terminal_route_destinations_refuse_repair(repair_app):
    _app, ctx = repair_app
    root = db.session.get(RouteLeg, ctx["leg_id"])
    db.session.add_all(
        [
            RouteLeg(
                parent_route_leg_id=root.id,
                route_plan_id=ctx["plan_id"],
                sequence_number=2,
                origin_location_id=ctx["destination_id"],
                destination_location_id=ctx["branch_a_id"],
                origin_snapshot={"display_name": "بندرعباس"},
                destination_snapshot={"display_name": "شیراز"},
                transport_mode="road",
                status="planned",
            ),
            RouteLeg(
                parent_route_leg_id=root.id,
                route_plan_id=ctx["plan_id"],
                sequence_number=3,
                origin_location_id=ctx["destination_id"],
                destination_location_id=ctx["branch_b_id"],
                origin_snapshot={"display_name": "بندرعباس"},
                destination_snapshot={"display_name": "یزد"},
                transport_mode="road",
                status="planned",
            ),
        ]
    )
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "ROUTE_TERMINAL_AMBIGUOUS" in _conflict_codes(result)


def test_d_existing_route_cargo_destination_refuses_repair(repair_app):
    _app, ctx = repair_app
    db.session.add(
        RouteCargoDestination(
            operational_shipment_id=ctx["shipment_id"],
            route_plan_id=ctx["plan_id"],
            shipment_cargo_item_id=ctx["cargo_id"],
            destination_route_leg_id=ctx["leg_id"],
            created_by_user_id=ctx["creator_id"],
        )
    )
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "EXISTING_CARGO_DESTINATION_CONFLICT" in _conflict_codes(result)


def test_e_existing_contradictory_requested_quantity_refuses_repair(repair_app):
    _app, ctx = repair_app
    cargo = db.session.get(ShipmentCargoItem, ctx["cargo_id"])
    cargo.source_shipment_request_id = ctx["request_id"]
    cargo.requested_quantity = Decimal("99")
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "PARTIAL_CONTINUITY_CONFLICT" in _conflict_codes(result)


def test_f_actual_quantity_contradiction_refuses_repair(repair_app):
    _app, ctx = repair_app
    cargo = db.session.get(ShipmentCargoItem, ctx["cargo_id"])
    cargo.actual_quantity = Decimal("95")
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "ACTUAL_QUANTITY_CONFLICT" in _conflict_codes(result)


def test_g_delivery_fact_conflict_refuses_repair(repair_app):
    _app, ctx = repair_app
    db.session.add(
        CargoDelivery(
            organization_id=ctx["org_id"],
            operational_shipment_id=ctx["shipment_id"],
            cargo_item_id=ctx["cargo_id"],
            quantity=Decimal("1"),
            uom_id=ctx["uom_id"],
            uom_code_snapshot="CCR_PIECE",
            uom_symbol_snapshot="pcs",
            destination_text="Existing delivery destination",
            occurred_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
            actor_user_id=ctx["creator_id"],
            revision=1,
        )
    )
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "DELIVERY_FACT_CONFLICT" in _conflict_codes(result)


def test_h_apply_preserves_timestamp_and_replay_is_singleton(repair_app):
    _app, ctx = repair_app
    plan = _plan(ctx)

    first = _apply(ctx, plan["plan_fingerprint"])
    second = _apply(ctx, plan["plan_fingerprint"])

    db.session.expire_all()
    cargo = db.session.get(ShipmentCargoItem, ctx["cargo_id"])
    audit = db.session.scalar(
        db.select(OperationalAudit).where(
            OperationalAudit.entity_type == "ShipmentCargoItem",
            OperationalAudit.entity_id == ctx["cargo_id"],
            OperationalAudit.action == REPAIR_ACTION,
        )
    )
    assert first["apply_result"] == "CHANGED"
    assert second["apply_result"] == "UNCHANGED"
    assert cargo.source_shipment_request_id == ctx["request_id"]
    assert cargo.source_request_cargo_item_id == ctx["source_cargo_id"]
    assert cargo.requested_quantity == Decimal("100")
    assert cargo.updated_at == ctx["preserved_updated_at"].replace(tzinfo=None)
    assert cargo.version == 2
    assert cargo.updated_by == ctx["admin_id"]
    assert _repair_counts(ctx) == {
        "mapping": 1,
        "audit": 1,
        "outbox": 1,
        "idempotency": 1,
    }
    assert audit.metadata_json["approval_reference"] == "ADR-072/operator-review-1"
    assert audit.metadata_json["operator"] == ADMIN_USERNAME
    assert audit.metadata_json["plan_fingerprint"] == plan["plan_fingerprint"]


def test_i_foreign_tenant_system_admin_is_denied(repair_app):
    _app, ctx = repair_app

    with pytest.raises(CargoContinuityRepairError) as exc_info:
        _plan(ctx, actor=FOREIGN_ADMIN_USERNAME)

    assert exc_info.value.code == "MAINTENANCE_TENANT_MISMATCH"


def test_j_ordinary_expert_is_denied_maintenance_authority(repair_app):
    _app, ctx = repair_app

    with pytest.raises(CargoContinuityRepairError) as exc_info:
        _plan(ctx, actor=EXPERT_USERNAME)

    assert exc_info.value.code == "MAINTENANCE_AUTHORITY_REQUIRED"


def test_inactive_maintenance_tenant_is_revalidated_and_denied(repair_app):
    _app, ctx = repair_app
    organization = db.session.get(OperationalOrganization, ctx["org_id"])
    organization.is_active = False
    db.session.commit()

    with pytest.raises(CargoContinuityRepairError) as exc_info:
        _plan(ctx)

    assert exc_info.value.code == "MAINTENANCE_TENANT_REQUIRED"


def test_l_direct_shipment_refuses_fabricated_request_lineage(repair_app):
    _app, ctx = repair_app
    shipment = db.session.get(OperationalShipment, ctx["shipment_id"])
    shipment.source_type = "direct"
    shipment.shipment_request_id = None
    shipment.accepted_quote_id = None
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "DIRECT_SHIPMENT_NOT_ELIGIBLE" in _conflict_codes(result)


def test_tampered_plan_fingerprint_rolls_back_without_writes(repair_app):
    _app, ctx = repair_app

    with pytest.raises(CargoContinuityRepairError) as exc_info:
        _apply(ctx, "0" * 64)

    assert exc_info.value.code == "REPAIR_PLAN_CHANGED"
    assert _repair_counts(ctx) == {
        "mapping": 0,
        "audit": 0,
        "outbox": 0,
        "idempotency": 0,
    }
    cargo = db.session.get(ShipmentCargoItem, ctx["cargo_id"])
    assert cargo.source_shipment_request_id is None
    assert cargo.source_request_cargo_item_id is None
    assert cargo.requested_quantity is None


def test_creation_defect_audit_must_match_tenant_and_creation_identity(repair_app):
    _app, ctx = repair_app
    audit = db.session.scalar(
        db.select(OperationalAudit).where(
            OperationalAudit.entity_type == "ShipmentCargoItem",
            OperationalAudit.entity_id == ctx["cargo_id"],
            OperationalAudit.action == "SHIPMENT_CARGO_CREATED",
        )
    )
    audit.organization_id = ctx["org_id"] + 1
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "KNOWN_DEFECT_SIGNATURE_NOT_PROVEN" in _conflict_codes(result)


def test_creation_defect_audit_requires_null_before_and_complete_changed_fields(
    repair_app,
):
    _app, ctx = repair_app
    audit = db.session.scalar(
        db.select(OperationalAudit).where(
            OperationalAudit.entity_type == "ShipmentCargoItem",
            OperationalAudit.entity_id == ctx["cargo_id"],
            OperationalAudit.action == "SHIPMENT_CARGO_CREATED",
        )
    )
    metadata = dict(audit.metadata_json)
    changes = dict(metadata["changes"])
    changes["requested_quantity"] = {"before": "100", "after": None}
    metadata["changes"] = changes
    metadata["changed_fields"] = ["requested_quantity"]
    audit.metadata_json = metadata
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "KNOWN_DEFECT_SIGNATURE_NOT_PROVEN" in _conflict_codes(result)


def test_customer_must_be_non_null_tenant_owned_identity(repair_app):
    _app, ctx = repair_app
    customer = Customer(
        first_name="Legacy",
        last_name="Quarantined",
        status="active",
        ownership_scope="LEGACY_QUARANTINED",
        operational_organization_id=None,
    )
    db.session.add(customer)
    db.session.flush()
    db.session.get(ShipmentRequest, ctx["request_id"]).customer_id = customer.id
    db.session.get(OperationalShipment, ctx["shipment_id"]).customer_id = customer.id
    db.session.get(ShipmentCargoItem, ctx["cargo_id"]).cargo_owner_customer_id = customer.id
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "COMMERCIAL_LINEAGE_CONFLICT" in _conflict_codes(result)


def test_one_leg_self_parent_is_not_a_provable_route(repair_app):
    _app, ctx = repair_app
    leg = db.session.get(RouteLeg, ctx["leg_id"])
    leg.parent_route_leg_id = leg.id
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "ROUTE_PATH_INVALID" in _conflict_codes(result)


def test_orphan_shipment_execution_refuses_repair(repair_app):
    _app, ctx = repair_app
    db.session.add(
        ExecutionUnit(
            organization_id=ctx["org_id"],
            operational_shipment_id=ctx["shipment_id"],
            unit_code="CCR-ORPHAN",
            unit_type="truck",
            created_by_user_id=ctx["creator_id"],
        )
    )
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "EXECUTION_ROUTE_CONFLICT" in _conflict_codes(result)


def test_existing_exact_execution_is_eligible_and_unchanged(repair_app):
    _app, ctx = repair_app
    unit = ExecutionUnit(
        organization_id=ctx["org_id"],
        operational_shipment_id=ctx["shipment_id"],
        unit_code="CCR-EXACT-EXECUTION",
        unit_type="truck",
        display_name="Existing walkthrough execution",
        created_by_user_id=ctx["creator_id"],
    )
    db.session.add(unit)
    db.session.flush()
    stage = RouteStageExecution(
        organization_id=ctx["org_id"],
        operational_shipment_id=ctx["shipment_id"],
        route_plan_id=ctx["plan_id"],
        route_leg_id=ctx["leg_id"],
        execution_unit_id=unit.id,
        idempotency_key="ccr-exact-execution",
        request_hash="e" * 64,
        created_by_user_id=ctx["creator_id"],
    )
    db.session.add(stage)
    db.session.commit()
    identity = (unit.id, unit.public_id, unit.version, unit.updated_at, stage.id)

    plan = _plan(ctx)
    first = _apply(ctx, plan["plan_fingerprint"])
    second = _apply(ctx, plan["plan_fingerprint"])

    db.session.expire_all()
    persisted_unit = db.session.get(ExecutionUnit, identity[0])
    persisted_stage = db.session.get(RouteStageExecution, identity[4])
    assert plan["eligibility"] == "YES"
    assert plan["existing_execution_public_ids"] == [identity[1]]
    assert first["apply_result"] == "CHANGED"
    assert second["apply_result"] == "UNCHANGED"
    assert (
        persisted_unit.public_id,
        persisted_unit.version,
        persisted_unit.updated_at,
    ) == identity[1:4]
    assert persisted_stage.execution_unit_id == persisted_unit.id
    assert persisted_stage.route_plan_id == ctx["plan_id"]
    assert persisted_stage.route_leg_id == ctx["leg_id"]


def test_allocation_must_match_exact_stage_execution_identity(repair_app):
    _app, ctx = repair_app
    stage_unit = ExecutionUnit(
        organization_id=ctx["org_id"],
        operational_shipment_id=ctx["shipment_id"],
        unit_code="CCR-STAGE",
        unit_type="truck",
        created_by_user_id=ctx["creator_id"],
    )
    other_unit = ExecutionUnit(
        organization_id=ctx["org_id"],
        operational_shipment_id=None,
        unit_code="CCR-OTHER",
        unit_type="truck",
        created_by_user_id=ctx["creator_id"],
    )
    db.session.add_all([stage_unit, other_unit])
    db.session.flush()
    stage = RouteStageExecution(
        organization_id=ctx["org_id"],
        operational_shipment_id=ctx["shipment_id"],
        route_plan_id=ctx["plan_id"],
        route_leg_id=ctx["leg_id"],
        execution_unit_id=stage_unit.id,
        idempotency_key="ccr-stage",
        request_hash="a" * 64,
        created_by_user_id=ctx["creator_id"],
    )
    db.session.add(stage)
    db.session.flush()
    db.session.add(
        ExecutionUnitCargoAllocation(
            execution_unit_id=other_unit.id,
            shipment_cargo_item_id=ctx["cargo_id"],
            operational_shipment_id=ctx["shipment_id"],
            project_id=None,
            route_stage_execution_id=stage.id,
            dimension="PLANNED",
            allocated_quantity=Decimal("100"),
            created_by=ctx["creator_id"],
            updated_by=ctx["creator_id"],
        )
    )
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "ALLOCATION_ROUTE_CONFLICT" in _conflict_codes(result)


def test_replay_requires_complete_atomic_audit_outbox_and_ledger(repair_app):
    _app, ctx = repair_app
    plan = _plan(ctx)
    _apply(ctx, plan["plan_fingerprint"])
    ledger = db.session.scalar(
        db.select(OperationalIdempotency).where(
            OperationalIdempotency.operation == IDEMPOTENCY_OPERATION,
            OperationalIdempotency.command_resource_id == ctx["shipment_id"],
        )
    )
    db.session.delete(ledger)
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "REPAIR_STATE_DRIFT" in _conflict_codes(result)


def test_replay_refuses_tampered_required_audit_metadata(repair_app):
    _app, ctx = repair_app
    plan = _plan(ctx)
    _apply(ctx, plan["plan_fingerprint"])
    audit = db.session.scalar(
        db.select(OperationalAudit).where(
            OperationalAudit.entity_type == "ShipmentCargoItem",
            OperationalAudit.entity_id == ctx["cargo_id"],
            OperationalAudit.action == REPAIR_ACTION,
        )
    )
    audit.metadata_json = {**audit.metadata_json, "terminal_route_leg_id": -1}
    db.session.commit()

    result = _plan(ctx)

    assert result["eligibility"] == "NO"
    assert "REPAIR_STATE_DRIFT" in _conflict_codes(result)


def test_apply_operator_must_match_authorized_actor(repair_app):
    _app, ctx = repair_app
    plan = _plan(ctx)

    with pytest.raises(CargoContinuityRepairError) as exc_info:
        apply_repair(
            ctx["shipment_public_id"],
            ADMIN_USERNAME,
            approval_reference="ADR-072/operator-review-1",
            expected_plan_fingerprint=plan["plan_fingerprint"],
            operator="self-asserted-other-operator",
            expected_request_tracking_code=TRACKING_CODE,
            expected_cargo_public_id=ctx["cargo_public_id"],
            expected_source_request_cargo_public_id=ctx["source_cargo_public_id"],
            expected_route_plan_id=ctx["plan_id"],
            expected_terminal_route_leg_id=ctx["leg_id"],
        )

    assert exc_info.value.code == "OPERATOR_IDENTITY_MISMATCH"
    assert _repair_counts(ctx) == {
        "mapping": 0,
        "audit": 0,
        "outbox": 0,
        "idempotency": 0,
    }


def test_cli_plan_and_identity_mismatch_are_machine_readable(
    repair_app, monkeypatch, capsys
):
    app, ctx = repair_app
    monkeypatch.setattr(repair_cli, "create_app", lambda **_kwargs: app)

    ok = repair_cli.main(
        [
            "plan",
            "--shipment",
            ctx["shipment_public_id"],
            "--actor-username",
            ADMIN_USERNAME,
            "--expected-request-tracking-code",
            TRACKING_CODE,
            *_cli_binding_args(ctx),
            "--expected-database-name",
            ":memory:",
        ]
    )
    ok_payload = json.loads(capsys.readouterr().out)
    mismatch = repair_cli.main(
        [
            "plan",
            "--shipment",
            ctx["shipment_public_id"],
            "--actor-username",
            ADMIN_USERNAME,
            "--expected-request-tracking-code",
            TRACKING_CODE.replace("0", "O"),
            *_cli_binding_args(ctx),
            "--expected-database-name",
            ":memory:",
        ]
    )
    mismatch_payload = json.loads(capsys.readouterr().out)

    assert ok == 0
    assert ok_payload["eligibility"] == "YES"
    assert mismatch == 3
    assert mismatch_payload["eligibility"] == "NO"
    assert "EXPECTED_SOURCE_REQUEST_MISMATCH" in {
        item["code"] for item in mismatch_payload["conflicts"]
    }
    assert _repair_counts(ctx) == {
        "mapping": 0,
        "audit": 0,
        "outbox": 0,
        "idempotency": 0,
    }


def test_cli_apply_requires_confirmation_and_explicit_request_identity(
    repair_app, monkeypatch, capsys
):
    app, ctx = repair_app
    monkeypatch.setattr(repair_cli, "create_app", lambda **_kwargs: app)
    args = [
        "apply",
        "--shipment",
        ctx["shipment_public_id"],
        "--actor-username",
        ADMIN_USERNAME,
        "--expected-request-tracking-code",
        TRACKING_CODE,
        *_cli_binding_args(ctx),
        "--expected-database-name",
        ":memory:",
        "--operator",
        ADMIN_USERNAME,
        "--approval-reference",
        "ADR-072/review",
        "--expected-plan-fingerprint",
        "0" * 64,
    ]

    assert repair_cli.main(args) == 2
    assert json.loads(capsys.readouterr().out) == {"error": "CONFIRMATION_REQUIRED"}
    with pytest.raises(SystemExit) as exc_info:
        repair_cli.main(
            [item for item in args if item not in {"--expected-request-tracking-code", TRACKING_CODE}]
        )
    assert exc_info.value.code == 2


def test_cli_refuses_unreviewed_database_identity(repair_app, monkeypatch, capsys):
    app, ctx = repair_app
    monkeypatch.setattr(repair_cli, "create_app", lambda **_kwargs: app)

    exit_code = repair_cli.main(
        [
            "plan",
            "--shipment",
            ctx["shipment_public_id"],
            "--actor-username",
            ADMIN_USERNAME,
            "--expected-request-tracking-code",
            TRACKING_CODE,
            *_cli_binding_args(ctx),
            "--expected-database-name",
            "a-different-database",
        ]
    )

    assert exit_code == 3
    assert json.loads(capsys.readouterr().out)["error"] == (
        "REPAIR_DATABASE_IDENTITY_MISMATCH"
    )


def test_cli_refuses_development_runtime_even_with_reviewed_identity(
    repair_app, monkeypatch, capsys
):
    app, ctx = repair_app
    app.config["APP_ENV"] = "development"
    app.config["TESTING"] = False
    monkeypatch.setattr(repair_cli, "create_app", lambda **_kwargs: app)

    exit_code = repair_cli.main(
        [
            "plan",
            "--shipment",
            ctx["shipment_public_id"],
            "--actor-username",
            ADMIN_USERNAME,
            "--expected-request-tracking-code",
            TRACKING_CODE,
            *_cli_binding_args(ctx),
            "--expected-database-name",
            ":memory:",
        ]
    )

    assert exit_code == 3
    assert json.loads(capsys.readouterr().out)["error"] == (
        "REPAIR_RUNTIME_NOT_AUTHORIZED"
    )


@pytest.mark.parametrize("environment_name", ["APP_ENV", "ENV", "FLASK_ENV"])
def test_cli_refuses_production_before_opening_application(
    repair_app, monkeypatch, capsys, environment_name
):
    _app, ctx = repair_app
    for name in ("APP_ENV", "ENV", "FLASK_ENV"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(environment_name, "production")
    monkeypatch.setattr(
        repair_cli,
        "create_app",
        lambda **_kwargs: pytest.fail("production guard must run before app creation"),
    )

    exit_code = repair_cli.main(
        [
            "plan",
            "--shipment",
            ctx["shipment_public_id"],
            "--actor-username",
            ADMIN_USERNAME,
            "--expected-request-tracking-code",
            TRACKING_CODE,
            *_cli_binding_args(ctx),
            "--expected-database-name",
            ":memory:",
        ]
    )

    assert exit_code == 3
    assert json.loads(capsys.readouterr().out) == {
        "error": "PRODUCTION_REPAIR_NOT_AUTHORIZED"
    }
