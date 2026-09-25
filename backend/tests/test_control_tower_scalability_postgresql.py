"""Owned PostgreSQL 18 qualification for the scalable Control Tower query."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from time import perf_counter
from uuid import NAMESPACE_URL, uuid4, uuid5

from alembic import command
import pytest
from sqlalchemy import create_engine, event, func, select, text, update
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, revision_status
from backend.mdpm_models import OperationalDocumentRequirement
from backend.models import (
    Customer,
    DocumentDefinition,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.oip_models import OipSituation
from backend.operational_models import (
    CanonicalLocation,
    DelayReason,
    ExceptionReason,
    ExecutionUnit,
    OperationalCheckpoint,
    OperationalDelay,
    OperationalEvent,
    OperationalEventLocationEvidence,
    OperationalException,
    Milestone,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    OperationalWorkItem,
    Project,
    RouteLeg,
    RoutePlan,
)
from backend.services.control_tower_read_model import compose_control_tower
from backend.services.control_tower_query import _ranked_population
from backend.services.control_tower_scope import ControlTowerScopeDenied
from backend.services import oip_service as oip


HEAD = "20261001_phase3_cargo_lineage"
NOW = datetime(2026, 9, 21, 12, tzinfo=timezone.utc)
ACTIVE_COUNT = 500


def _url() -> str:
    url = os.environ.get("CONTROL_TOWER_DISPOSABLE_POSTGRES_URL")
    if not url:
        pytest.skip("owned disposable Control Tower PostgreSQL URL required")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.port == 55432
    assert parsed.database == "forwarder_control_tower_build"
    return url


def _reset(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(url), HEAD)
    engine.dispose()


def _member(organization, username, authority="EXPERT"):
    user = ExpertUser(
        username=username,
        full_name=username.replace("_", " ").title(),
        password_hash="not-a-login-credential",
        role="admin" if authority != "EXPERT" else "expert",
        authority=authority,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    membership = OperationalMembership(
        organization_id=organization.id,
        user_id=user.id,
        is_active=True,
        permissions=["operational_shipment.read"],
    )
    db.session.add(membership)
    db.session.flush()
    return user, membership


def _seed(app):
    with app.app_context():
        organization = OperationalOrganization(
            public_id=str(uuid4()), name="Control Tower qualification", is_active=True
        )
        foreign_organization = OperationalOrganization(
            public_id=str(uuid4()), name="Foreign qualification", is_active=True
        )
        db.session.add_all([organization, foreign_organization])
        db.session.flush()
        owner_a, owner_a_membership = _member(organization, "control_tower_owner_a")
        owner_b, _ = _member(organization, "control_tower_owner_b")
        admin, _ = _member(organization, "control_tower_admin", "ORGANIZATION_ADMIN")
        foreign_owner, _ = _member(foreign_organization, "foreign_control_tower_owner")
        platform = ExpertUser(
            username="control_tower_platform",
            full_name="Control Tower Platform",
            password_hash="not-a-login-credential",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        db.session.add(platform)
        customers = [
            Customer(
                operational_organization_id=tenant.id,
                ownership_scope="TENANT",
                first_name="Qualification",
                last_name=tenant.name,
                phone=f"0912{tenant.id:08d}"[-11:],
                status="active",
            )
            for tenant in (organization, foreign_organization)
        ]
        db.session.add_all(customers)
        db.session.flush()

        accepted_request = ShipmentRequest(
            operational_organization_id=organization.id,
            ownership_scope="TENANT",
            assigned_to=owner_a.id,
            contact_phone="09120000001",
        )
        db.session.add(accepted_request)
        db.session.flush()
        accepted_quote = ExpertQuote(
            shipment_request_id=accepted_request.id,
            amount=1,
            created_by_expert_id=owner_a.id,
            operational_organization_id=organization.id,
        )
        db.session.add(accepted_quote)
        db.session.flush()

        reasons = [
            DelayReason(
                organization_id=organization.id,
                immutable_code="QUALIFICATION_DELAY",
                fa_name="تأخیر آزمون",
                en_name="Qualification delay",
                created_by_user_id=owner_a.id,
                updated_by_user_id=owner_a.id,
            ),
            ExceptionReason(
                organization_id=organization.id,
                immutable_code="QUALIFICATION_EXCEPTION",
                fa_name="استثنای آزمون",
                en_name="Qualification exception",
                created_by_user_id=owner_a.id,
                updated_by_user_id=owner_a.id,
            ),
            DelayReason(
                organization_id=foreign_organization.id,
                immutable_code="FOREIGN_QUALIFICATION_DELAY",
                fa_name="تأخیر خارجی",
                en_name="Foreign qualification delay",
                created_by_user_id=foreign_owner.id,
                updated_by_user_id=foreign_owner.id,
            ),
        ]
        db.session.add_all(reasons)
        db.session.flush()
        delay_reason, exception_reason, foreign_delay_reason = reasons

        active = []
        for index in range(ACTIVE_COUNT):
            source = (
                {
                    "source_type": "accepted_quote",
                    "shipment_request_id": accepted_request.id,
                    "accepted_quote_id": accepted_quote.id,
                    "primary_responsible_expert_id": owner_a.id,
                }
                if index == 490
                else {
                    "source_type": "direct",
                    "customer_id": customers[0].id,
                    "primary_responsible_expert_id": (
                        owner_a if index % 2 == 0 else owner_b
                    ).id,
                }
            )
            active.append(OperationalShipment(
                public_id=str(uuid5(NAMESPACE_URL, f"control-tower-qualification-{index}")),
                organization_id=organization.id,
                lifecycle_status="planned" if index % 2 else "in_progress",
                created_by_user_id=(owner_a if index % 2 == 0 else owner_b).id,
                **source,
            ))
        terminal = [
            OperationalShipment(
                public_id=str(uuid5(NAMESPACE_URL, f"control-tower-terminal-{index}")),
                organization_id=organization.id,
                source_type="direct",
                customer_id=customers[0].id,
                lifecycle_status="completed",
                created_by_user_id=owner_a.id,
                primary_responsible_expert_id=owner_a.id,
            )
            for index in range(50)
        ]
        foreign = [
            OperationalShipment(
                public_id=str(uuid5(NAMESPACE_URL, f"control-tower-foreign-{index}")),
                organization_id=foreign_organization.id,
                source_type="direct",
                customer_id=customers[1].id,
                lifecycle_status="planned",
                created_by_user_id=foreign_owner.id,
                primary_responsible_expert_id=foreign_owner.id,
            )
            for index in range(25)
        ]
        db.session.add_all([*active, *terminal, *foreign])
        db.session.flush()
        execution_reasons = [
            (
                OperationalException(
                    organization_id=organization.id,
                    operational_shipment_id=shipment.id,
                    reason_id=exception_reason.id,
                    occurred_at=NOW - timedelta(minutes=index),
                    created_by_user_id=shipment.created_by_user_id,
                )
                if index % 3 == 1
                else OperationalDelay(
                    organization_id=organization.id,
                    operational_shipment_id=shipment.id,
                    reason_id=delay_reason.id,
                    started_at=NOW - timedelta(minutes=index),
                    created_by_user_id=shipment.created_by_user_id,
                )
            )
            for index, shipment in enumerate([*active, *terminal])
        ]
        db.session.add_all(execution_reasons)
        db.session.add_all([
            OperationalDelay(
                organization_id=foreign_organization.id,
                operational_shipment_id=shipment.id,
                reason_id=foreign_delay_reason.id,
                started_at=NOW - timedelta(minutes=index),
                created_by_user_id=foreign_owner.id,
            )
            for index, shipment in enumerate(foreign)
        ])

        origin = CanonicalLocation(
            source_type="city", source_id=9001, location_type="city", display_name="تهران"
        )
        destination = CanonicalLocation(
            source_type="city", source_id=9002, location_type="city", display_name="استانبول"
        )
        db.session.add_all([origin, destination])
        db.session.flush()
        urgent = active[::10]
        plans = [
            RoutePlan(
                operational_shipment_id=shipment.id,
                created_by_user_id=shipment.created_by_user_id,
            )
            for shipment in urgent
        ]
        db.session.add_all(plans)
        db.session.flush()
        legs = [
            RouteLeg(
                route_plan_id=plan.id,
                sequence_number=1,
                origin_location_id=origin.id,
                destination_location_id=destination.id,
                origin_snapshot={"display_name": "تهران"},
                destination_snapshot={"display_name": "استانبول"},
                transport_mode="road" if index % 2 == 0 else "rail",
                planned_departure=NOW - timedelta(days=1),
                planned_arrival=NOW + timedelta(days=1),
            )
            for index, plan in enumerate(plans)
        ]
        db.session.add_all(legs)
        db.session.flush()
        checkpoints = [
            OperationalCheckpoint(
                route_plan_id=plan.id,
                route_leg_id=leg.id,
                sequence_number=1,
                checkpoint_type="border_entry",
                canonical_location_id=destination.id,
                planned_arrival_at=NOW - timedelta(hours=2),
                created_by_user_id=shipment.created_by_user_id,
            )
            for shipment, plan, leg in zip(urgent, plans, legs)
        ]
        db.session.add_all(checkpoints)
        db.session.flush()
        db.session.add_all([
            OperationalWorkItem(
                organization_id=organization.id,
                operational_shipment_id=shipment.id,
                route_plan_id=plan.id,
                checkpoint_id=checkpoint.id,
                work_type="ROUTE_DEPENDENCY_BLOCKED",
                severity="critical",
                due_at=NOW - timedelta(hours=2),
                detected_at=NOW - timedelta(minutes=index),
                reason="qualification route dependency",
                assignee_user_id=shipment.created_by_user_id,
            )
            for index, (shipment, plan, checkpoint) in enumerate(
                zip(urgent, plans, checkpoints)
            )
        ])

        readiness_milestone = Milestone(
            organization_id=organization.id,
            operational_shipment_id=active[490].id,
            route_plan_id=plans[49].id,
            checkpoint_id=checkpoints[49].id,
            milestone_type="ARRIVAL",
            sequence=1,
            lifecycle_status="PENDING",
            planned_at=NOW + timedelta(hours=1),
        )
        readiness_definition = DocumentDefinition(
            code="CT-SCALABILITY-BILL-OF-LADING",
            title="بارنامه",
            allowed_formats='["pdf"]',
            max_file_size_bytes=1000,
        )
        db.session.add_all([readiness_milestone, readiness_definition])
        db.session.flush()
        db.session.add(OperationalDocumentRequirement(
            organization_id=organization.id,
            operational_shipment_id=active[490].id,
            document_definition_id=readiness_definition.id,
            requirement_level="CONDITIONAL",
            applicability_state="UNRESOLVED",
            target_milestone_type="ARRIVAL",
            target_status="READY",
            created_by_user_id=owner_a.id,
        ))

        project = Project(
            organization_id=organization.id,
            primary_customer_id=customers[0].id,
            project_code="CT-SCALABILITY-TRACKING",
            created_by_user_id=owner_a.id,
        )
        db.session.add(project)
        db.session.flush()
        tracked = urgent[-5:]
        units = []
        for index, shipment in enumerate(tracked):
            shipment.project_id = project.id
            unit = ExecutionUnit(
                organization_id=organization.id,
                project_id=project.id,
                operational_shipment_id=shipment.id,
                unit_code=f"CT-UNIT-{index}",
                unit_type="truck",
                lifecycle_status="in_progress",
                created_by_user_id=shipment.created_by_user_id,
            )
            db.session.add(unit)
            units.append(unit)
        db.session.flush()
        for index, unit in enumerate(units):
            row = OperationalEvent(
                project_id=project.id,
                execution_unit_id=unit.id,
                event_type="arrived",
                lifecycle_status="arrived",
                occurred_at=NOW - timedelta(hours=3, minutes=index),
                recorded_at=NOW - timedelta(hours=1, minutes=index),
                actor_user_id=owner_a.id,
                idempotency_key=f"ct-scalability-{index}",
                request_hash=f"ct-scalability-hash-{index}",
            )
            db.session.add(row)
            db.session.flush()
            db.session.add(OperationalEventLocationEvidence(
                operational_event_id=row.id,
                source_type="manual",
                display_name_snapshot="بندرعباس",
            ))
        db.session.commit()
        result = {
            "organization": organization.id,
            "active_ids": [shipment.id for shipment in active],
            "active_public_ids": [shipment.public_id for shipment in active],
            "owner_a": owner_a.id,
            "owner_a_membership": owner_a_membership.id,
            "admin": admin.id,
            "foreign_owner": foreign_owner.id,
            "platform": platform.id,
            "accepted_request_public_id": accepted_request.public_id,
            "oip_candidate": {
                "shipment_public_id": active[2].public_id,
                "source_public_id": execution_reasons[2].public_id,
                "source_version": execution_reasons[2].version,
                "occurred_at": execution_reasons[2].started_at,
            },
        }
        db.session.remove()
        return result


def _set_active_count(seed, count):
    ids = seed["active_ids"]
    db.session.execute(update(OperationalShipment).where(
        OperationalShipment.id.in_(ids)
    ).values(lifecycle_status="completed"))
    if count:
        db.session.execute(update(OperationalShipment).where(
            OperationalShipment.id.in_(ids[:count])
        ).values(lifecycle_status="planned"))
    db.session.commit()
    db.session.expire_all()


def _expected_urgent(count):
    return 0 if count == 0 else (count - 1) // 10 + 1


def test_control_tower_owned_postgresql_release_scale_contract():
    url = _url()
    _reset(url)
    assert revision_status(url).current == (HEAD,)
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": url,
        "SECRET_KEY": "owned-control-tower-qualification",
    }, skip_startup=True)
    seed = _seed(app)
    with app.app_context():
        admin = {"id": seed["admin"]}
        size_results = {}
        for size in (0, 1, 99, 100, 101, 250, 500):
            _set_active_count(seed, size)
            result = compose_control_tower(admin, page_size=25, at=NOW)
            urgent = _expected_urgent(size)
            assert result.state == "complete"
            assert result.summary.total == size
            assert result.summary.attention_counts == {
                "urgent": urgent,
                "follow_up": size - urgent,
                "review": 0,
            }
            assert result.page.returned == min(size, 25)
            assert result.page.has_more is (size > 25)
            size_results[size] = result

        first_references = [
            item.shipment_reference for item in size_results[500].items
        ]
        repeated = compose_control_tower(admin, page_size=25, at=NOW)
        assert [item.shipment_reference for item in repeated.items] == first_references
        assert all(item.attention == "urgent" for item in repeated.items)
        assert all(item.route_label == "تهران → استانبول" for item in repeated.items)
        assert any(item.progress["source"] == "operational_event" for item in repeated.items)

        references = []
        cursor = None
        while True:
            window = compose_control_tower(
                admin, page_size=100, cursor=cursor, at=NOW
            )
            references.extend(item.shipment_reference for item in window.items)
            cursor = window.page.next_cursor
            if cursor is None:
                break
        assert len(references) == 500
        assert len(set(references)) == 500
        assert set(references) == set(seed["active_public_ids"])

        urgent = compose_control_tower(
            admin, page_size=25, attention="urgent", at=NOW
        )
        assert urgent.summary.total == 50
        assert urgent.summary.attention_counts == {
            "urgent": 50,
            "follow_up": 450,
            "review": 0,
        }
        searched = compose_control_tower(
            admin, page_size=25, search=seed["active_public_ids"][499], at=NOW
        )
        assert searched.summary.total == 1
        assert searched.items[0].shipment_reference == seed["active_public_ids"][499]
        request_search = compose_control_tower(
            admin,
            page_size=25,
            search=seed["accepted_request_public_id"],
            at=NOW,
        )
        assert request_search.summary.total == 1
        assert request_search.items[0].shipment_reference == seed["active_public_ids"][490]
        owner_search = compose_control_tower(
            admin, page_size=25, search="Control Tower Owner A", at=NOW
        )
        assert owner_search.summary.total == 250

        owner_view = compose_control_tower(
            {"id": seed["owner_a"]}, page_size=25, at=NOW
        )
        assert owner_view.summary.total == 250
        assert all(item.owner_name == "Control Tower Owner A" for item in owner_view.items)
        foreign_view = compose_control_tower(
            {"id": seed["foreign_owner"]}, page_size=25, at=NOW
        )
        assert foreign_view.summary.total == 25
        with pytest.raises(ControlTowerScopeDenied):
            compose_control_tower({"id": seed["platform"]}, page_size=25, at=NOW)

        candidate = seed["oip_candidate"]
        observation = oip.observe(
            organization_id=seed["organization"],
            situation_type="ACTIVE_DELAY_OR_EXCEPTION",
            subject_type="SHIPMENT",
            subject_public_id=candidate["shipment_public_id"],
            dimensions={
                "source_type": "OperationalDelay",
                "source_public_id": candidate["source_public_id"],
            },
            source_domain="OPERATIONAL_EXECUTION",
            source_type="OperationalDelay",
            source_public_id=candidate["source_public_id"],
            source_version=candidate["source_version"],
            occurred_at=candidate["occurred_at"],
            severity="HIGH",
            urgency="HIGH",
            calculated_at=NOW,
            evidence={"kind": "qualification"},
        )
        db.session.commit()
        promoted = compose_control_tower(
            admin,
            page_size=25,
            search=candidate["shipment_public_id"],
            at=NOW,
        )
        assert promoted.summary.total == 1
        assert promoted.items[0].attention == "urgent"
        situation = OipSituation.query.filter_by(
            public_id=observation["public_id"]
        ).one()
        situation.status = "RESOLVED"
        situation.resolved_at = NOW
        db.session.commit()

        initial = compose_control_tower(admin, page_size=25, at=NOW)
        db.session.execute(update(OperationalShipment).where(
            OperationalShipment.id == seed["active_ids"][-1]
        ).values(lifecycle_status="completed"))
        db.session.commit()
        changed = compose_control_tower(
            admin, page_size=25, cursor=initial.page.next_cursor, at=NOW
        )
        assert changed.summary.total == 499
        assert changed.page.offset == 25
        _set_active_count(seed, 500)

        membership = db.session.get(
            OperationalMembership, seed["owner_a_membership"]
        )
        membership.is_active = False
        db.session.commit()
        with pytest.raises(ControlTowerScopeDenied):
            compose_control_tower({"id": seed["owner_a"]}, page_size=25, at=NOW)
        membership.is_active = True
        db.session.commit()

        def measure(page_size):
            statements = []

            def capture(conn, cursor, statement, parameters, context, many):
                statements.append(statement)

            event.listen(db.engine, "before_cursor_execute", capture)
            started = perf_counter()
            try:
                measured = compose_control_tower(
                    admin, page_size=page_size, at=NOW
                )
            finally:
                elapsed = perf_counter() - started
                event.remove(db.engine, "before_cursor_execute", capture)
            return measured, elapsed, statements

        measured, elapsed, statements = measure(25)
        wide_page, wide_elapsed, wide_statements = measure(100)
        assert measured.summary.total == 500
        assert wide_page.summary.total == 500
        assert wide_page.page.returned == 100
        assert elapsed < 30
        assert wide_elapsed < 30
        # Both windows include the accepted-quote readiness branch. Its
        # relational query family is fixed, and widening the page must not add
        # per-shipment statements.
        assert len(statements) < 100
        assert len(wide_statements) < 100
        assert len(wide_statements) <= len(statements)

        ranked = _ranked_population(admin, NOW, None)
        aggregate = select(func.count()).select_from(ranked)
        compiled = aggregate.compile(
            dialect=db.engine.dialect,
            compile_kwargs={"literal_binds": True},
        )
        explain = db.session.execute(text(
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + str(compiled)
        )).scalar_one()[0]
        assert explain["Execution Time"] < 1000
        print("CONTROL_TOWER_POSTGRESQL_METRICS=" + json.dumps({
            "active_population": 500,
            "terminal_same_tenant": 50,
            "foreign_active": 25,
            "page_size": 25,
            "query_count": len(statements),
            "elapsed_seconds": round(elapsed, 3),
            "wide_page_size": 100,
            "wide_query_count": len(wide_statements),
            "wide_elapsed_seconds": round(wide_elapsed, 3),
            "aggregate_plan_execution_ms": round(explain["Execution Time"], 3),
            "aggregate_plan_planning_ms": round(explain["Planning Time"], 3),
            "aggregate_plan_rows": explain["Plan"]["Actual Rows"],
            "traversed": len(references),
        }, sort_keys=True))
        db.session.remove()
