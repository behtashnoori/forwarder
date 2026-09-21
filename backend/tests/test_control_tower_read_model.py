"""Slice 3 composition, ordering, continuation and disclosure boundaries."""
import base64
from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import timedelta

import pytest
from sqlalchemy import event, update

from backend.extensions import db
from backend.models import Customer, DocumentDefinition
from backend.mdpm_models import OperationalDocumentRequirement
from backend.operational_models import (
    CanonicalLocation,
    ExecutionUnit,
    Milestone,
    OperationalCheckpoint,
    OperationalEvent,
    OperationalEventLocationEvidence,
    OperationalShipment,
    Project,
    RouteLeg,
    RoutePlan,
)
from backend.services import control_tower_read_model as model, control_tower_sources as sources
from backend.services.control_tower_oip import VerifiedEnrichment
from backend.services.control_tower_scope import ControlTowerScopeDenied, ControlTowerResponsibilityInvariant
from backend.services.control_tower_translation import (
    AttentionLevel as Level, EMPTY_MESSAGE, Semantic, UNAVAILABLE_MESSAGE, time_context, translate,
)
from backend.tests.test_control_tower_scope import tower  # noqa: F401
from backend.tests.test_control_tower_sources import attention, NOW, PRIVATE, _observe  # noqa: F401


def reason(key, *, level=Level.FOLLOW_UP, due=None, opened=None, family="OperationalDelay",
           linkage=(), severity=None, enrichment=(), version=1, semantic=Semantic.ACTIVE_DELAY):
    title, explanation = translate(semantic)
    times = tuple(t for t in (time_context("expected_due", due), time_context("work_open", opened)) if t)
    return sources.AttentionReason(semantic, level, title, explanation, times,
        sources.SourceIdentity(family, key, version, linkage), enrichment, severity)


def stub(monkeypatch, mapping):
    monkeypatch.setattr(sources, "evaluate_bounded_sources", lambda actor, contexts, **kw: tuple(
        (context, mapping.get(context.shipment_id, ())) for context in contexts))


def read(actor, **kw):
    return model.compose_control_tower({"id": actor.id}, at=NOW, **kw)


@pytest.mark.parametrize("number", [0, 1, 3])
def test_one_shipment_at_most_one_item_and_complete_empty(tower, monkeypatch, number):
    shipment, _ = tower.shipment()
    stub(monkeypatch, {shipment.id: tuple(reason(str(i)) for i in range(number))})
    result = read(tower.a)
    assert result.state == "complete" and result.notice is None
    assert len(result.items) == bool(number)
    assert result.empty_message == (EMPTY_MESSAGE if not number else None)
    if number:
        item, = result.items
        assert item.shipment_reference == shipment.public_id
        assert item.destination == f"/operations/shipments/{shipment.public_id}"
        assert len(item.additional_reasons) == number - 1


def test_real_sources_enrichment_and_distinct_records_remain_one_card(attention):
    delay, _ = attention.execution()
    situation = _observe(attention, delay)
    situation.assignee_user_id = attention.tower.b.id
    db.session.commit()
    attention.execution(exception=True)
    attention.work()
    attention.requirement()
    result = read(attention.tower.a)
    item, = result.items
    assert item.attention == "urgent"
    assert item.primary_reason.semantic == "delay_open"
    assert len(item.additional_reasons) == 3
    assert {r.semantic for r in item.additional_reasons} == {
        "exception_open", "route_follow_up", "documents_blocked"}
    assert item.owner_name == attention.context.responsible_expert_name
    assert item.owner_name != attention.tower.b.full_name  # WorkItem assignee
    assert item.attention_label == "اقدام فوری"


def test_proven_work_duplicates_choose_latest_occurrence_only():
    old = reason("1", family="OperationalWorkItem", linkage=("REPLAN_REQUIRED", 1, 2, None),
                 opened=NOW-timedelta(days=10))
    new = replace(old, source_identity=replace(old.source_identity, key="2"),
                  time_context=(time_context("work_open", NOW-timedelta(hours=1)),))
    independent = replace(old, source_identity=replace(old.source_identity, key="3", linkage=("REPLAN_REQUIRED", 1, 3, None)))
    assert {r.source_identity.key for r in model._ordered_reasons((old, new, independent), NOW)} == {"2", "3"}
    milestone_old = replace(old, source_identity=sources.SourceIdentity(
        "OperationalWorkItem", "4", 1, ("OVERDUE_MILESTONE", None, None, 10)))
    milestone_new = replace(new, source_identity=sources.SourceIdentity(
        "OperationalWorkItem", "5", 1, ("OVERDUE_MILESTONE", 1, None, 10)))
    assert model._ordered_reasons((milestone_old, milestone_new), NOW) == (milestone_new,)


@pytest.mark.parametrize("low,high", [(Level.REVIEW, Level.FOLLOW_UP), (Level.FOLLOW_UP, Level.URGENT)])
def test_attention_precedence_overrides_time(low, high):
    first = reason("old", level=low, due=NOW-timedelta(days=20))
    second = reason("new", level=high)
    assert model._ordered_reasons((first, second), NOW)[0] == second


def test_due_groups_then_earlier_due_then_oldest_onset_and_stable_identity():
    reasons = (
        reason("none", opened=NOW-timedelta(days=30)),
        reason("future_late", due=NOW+timedelta(days=3)),
        reason("overdue_late", due=NOW-timedelta(days=1)),
        reason("future_early", due=NOW+timedelta(days=1)),
        reason("overdue_early", due=NOW-timedelta(days=3)),
        reason("none_new", opened=NOW-timedelta(days=1)),
        reason("missing_b"), reason("missing_a"),
    )
    expected = ["overdue_early", "overdue_late", "future_early", "future_late", "none", "none_new", "missing_a", "missing_b"]
    for values in (reasons, tuple(reversed(reasons))):
        assert [r.source_identity.key for r in model._ordered_reasons(values, NOW)] == expected
    same_due = [reason("new", due=NOW, opened=NOW-timedelta(days=1)),
                reason("old", due=NOW, opened=NOW-timedelta(days=2))]
    assert model._ordered_reasons(same_due, NOW)[0].source_identity.key == "old"


def test_evaluated_time_is_not_open_condition_age():
    readiness = replace(reason("a"), time_context=(time_context("evaluated", NOW-timedelta(days=30)),))
    opened = reason("z", opened=NOW-timedelta(days=1))
    assert model._ordered_reasons((readiness, opened), NOW)[0] == opened


def test_comparable_work_severity_then_cross_model_time_without_rank_normalization():
    warning = reason("warning", level=Level.URGENT, family="OperationalWorkItem",
        linkage=("REPLAN_REQUIRED", 1, 1, None), severity="warning", due=NOW-timedelta(days=10))
    critical = reason("critical", level=Level.URGENT, family="OperationalWorkItem",
        linkage=("REPLAN_REQUIRED", 1, 2, None), severity="critical", due=NOW-timedelta(days=1))
    independent = reason("delay", level=Level.URGENT, due=NOW-timedelta(days=2))
    assert model._ordered_reasons((warning, critical), NOW)[0] == critical
    assert model._ordered_reasons((warning, critical, independent), NOW)[0] == independent
    # Product F.8 card time is earliest same-level due even when primary differs.
    ordered = model._ordered_reasons((warning, critical), NOW)
    assert model._shipment_order(ordered, "shipment", NOW)[2] == warning.time_context[0].at


def test_oip_rank_only_within_identical_policy_and_version():
    enrich = lambda policy, version, urgency, severity: (
        VerifiedEnrichment(policy, version, urgency, severity, True),)
    old = reason("old", level=Level.URGENT, due=NOW-timedelta(days=10),
                 enrichment=enrich("policy", "1", "HIGH", "CRITICAL"))
    best = reason("best", level=Level.URGENT, due=NOW-timedelta(days=1),
                  enrichment=enrich("policy", "1", "CRITICAL", "LOW"))
    assert model._ordered_reasons((old, best), NOW)[0] == best
    for independent in (replace(old, enrichment=enrich("other", "1", "LOW", "LOW")),
                        replace(old, enrichment=enrich("policy", "2", "LOW", "LOW"))):
        assert model._ordered_reasons((independent, best), NOW)[0] == independent


def add_leg(env, sequence=1, *, plan=None, mode="road", origin=None, destination=None, **changes):
    start = origin or env.location
    end = destination or CanonicalLocation(source_type="city", source_id=sequence+10,
                                            location_type="city", display_name="استانبول")
    db.session.add(end)
    db.session.flush()
    row = RouteLeg(route_plan_id=(plan or env.plan).id, sequence_number=sequence,
        origin_location_id=start.id, destination_location_id=end.id,
        origin_snapshot={"display_name": start.display_name, "private": PRIVATE},
        destination_snapshot={"display_name": end.display_name, "private": PRIVATE},
        transport_mode=mode, planned_departure=NOW, planned_arrival=NOW+timedelta(hours=2))
    for key, value in changes.items():
        setattr(row, key, value)
    db.session.add(row)
    db.session.commit()
    return row, end


@pytest.mark.parametrize("mode,label", [("road", "جاده‌ای"), ("rail", "ریلی"), ("sea", "دریایی"), ("air", "هوایی")])
def test_active_route_safe_snapshots_and_unambiguous_transport(attention, mode, label):
    attention.execution()
    add_leg(attention, mode=mode)
    item, = read(attention.tower.a).items
    assert item.route_label == "تهران → استانبول"
    assert item.transport_label == label
    assert item.actual_route_modes == (mode,)
    assert PRIVATE not in repr(asdict(item))


@pytest.mark.parametrize("modes,label", [
    (("road", "rail"), "ترکیبی"),
    (("road", "sea"), "ترکیبی"),
    (("air", "road"), "ترکیبی"),
    (("road", "road"), "جاده‌ای"),
])
def test_current_continuous_actual_transport_modes(attention, modes, label):
    attention.execution()
    _, middle = add_leg(attention, mode=modes[0])
    end = CanonicalLocation(source_type="city", source_id=99,
                            location_type="city", display_name="آنکارا")
    add_leg(attention, sequence=2, origin=middle, destination=end, mode=modes[1])
    item, = read(attention.tower.a).items
    assert item.route_label == "تهران → آنکارا"
    assert item.transport_label == label
    assert item.actual_route_modes == modes


def test_canonical_tracking_progress_preserves_occurred_and_recorded(attention):
    attention.execution()
    customer = Customer.query.one()
    project = Project(
        organization_id=attention.tower.org.id,
        primary_customer_id=customer.id,
        project_code="CT-TRACKING",
        created_by_user_id=attention.tower.a.id,
    )
    db.session.add(project)
    db.session.flush()
    attention.shipment.project_id = project.id
    unit = ExecutionUnit(
        organization_id=attention.tower.org.id,
        project_id=project.id,
        operational_shipment_id=attention.shipment.id,
        unit_code="CT-U-1",
        unit_type="truck",
        lifecycle_status="in_progress",
        created_by_user_id=attention.tower.a.id,
    )
    db.session.add(unit)
    db.session.flush()
    occurred = NOW - timedelta(hours=3)
    recorded = NOW - timedelta(hours=1)
    event_row = OperationalEvent(
        project_id=project.id,
        execution_unit_id=unit.id,
        event_type="arrived",
        lifecycle_status="arrived",
        occurred_at=occurred,
        recorded_at=recorded,
        actor_user_id=attention.tower.a.id,
        idempotency_key="ct-progress",
        request_hash="ct-progress-hash",
    )
    db.session.add(event_row)
    db.session.flush()
    db.session.add(
        OperationalEventLocationEvidence(
            operational_event_id=event_row.id,
            source_type="manual",
            display_name_snapshot="بندرعباس",
        )
    )
    db.session.commit()

    item, = read(attention.tower.a).items
    assert item.progress["currentLocation"] == "بندرعباس"
    assert item.progress["latestEventOccurredAt"] == "2026-09-17T09:00:00Z"
    assert item.progress["latestEventRecordedAt"] == "2026-09-17T11:00:00Z"
    assert item.progress["source"] == "operational_event"


@pytest.mark.parametrize("modes", [
    ("unsupported",), ("customs_handling",), ("multimodal_transfer",),
    ("road", "unsupported"), ("road", "customs_handling"),
    ("road", "multimodal_transfer"), ("customs_handling", "multimodal_transfer"),
])
def test_unknown_and_operational_transport_context_is_omitted(attention, modes):
    attention.execution()
    origin = attention.location
    for sequence, mode in enumerate(modes, start=1):
        _, origin = add_leg(attention, sequence=sequence, origin=origin, mode=mode)
    item, = read(attention.tower.a).items
    assert item.route_label == "تهران → استانبول"
    assert item.transport_label is None
    assert item.actual_route_modes == modes


@pytest.mark.parametrize("damage", ["superseded", "draft", "cancelled_leg", "no_legs", "protected_label", "protected_multimode", "broken_chain", "handling", "transfer"])
def test_route_absence_history_and_ambiguity_are_omitted(attention, damage):
    attention.execution()
    leg, end = add_leg(attention)
    if damage in {"superseded", "draft"}:
        attention.plan.status = damage
        attention.plan.is_active = False
    elif damage == "cancelled_leg":
        leg.status = "cancelled"
    elif damage == "no_legs":
        db.session.delete(leg)
    elif damage in {"protected_label", "protected_multimode"}:
        leg.origin_snapshot = {"display_name": "هزینه حمل"}
        if damage == "protected_multimode":
            add_leg(attention, sequence=2, origin=end, mode="rail")
    elif damage == "broken_chain":
        add_leg(attention, sequence=2, mode="rail")  # disconnected from first end
    elif damage == "handling":
        leg.transport_mode = "customs_handling"
    else:
        leg.transport_mode = "multimodal_transfer"
    db.session.commit()
    item, = read(attention.tower.a).items
    if damage not in {"handling", "transfer"}:
        assert item.route_label is None
    assert item.transport_label is None


def test_missing_route_and_historical_plan_not_used(tower, monkeypatch):
    shipment, _ = tower.shipment()
    plan = RoutePlan(operational_shipment_id=shipment.id, status="superseded", is_active=False,
                     created_by_user_id=tower.a.id)
    db.session.add(plan)
    db.session.commit()
    stub(monkeypatch, {shipment.id: (reason("only"),)})
    item, = read(tower.a).items
    assert item.route_label is None and item.transport_label is None


def test_shipments_sorted_and_aggregated_before_stable_pagination(tower, monkeypatch):
    shipments = [tower.shipment()[0] for _ in range(7)]
    mapping = {
        shipments[1].id: (reason("follow_late", due=NOW+timedelta(days=3)),),
        shipments[2].id: (reason("review", level=Level.REVIEW),),
        shipments[3].id: (reason("urgent", level=Level.URGENT), reason("extra")),
        shipments[4].id: (reason("follow_early", due=NOW-timedelta(days=3)),),
        shipments[5].id: (reason("follow_old", opened=NOW-timedelta(days=3)),),
        shipments[6].id: (reason("follow_new", opened=NOW-timedelta(days=1)),),
    }
    stub(monkeypatch, mapping)
    expected = [shipments[i].public_id for i in (3, 4, 1, 5, 6, 2)]
    references, cursor = [], None
    for _ in range(3):
        result = read(tower.a, page_size=2, cursor=cursor)
        assert len(result.items) == 2
        assert result.empty_message is None
        references.extend(item.shipment_reference for item in result.items)
        cursor = result.page.next_cursor
    assert references == expected and cursor is None
    assert len(set(references)) == 6
    with pytest.raises(FrozenInstanceError):
        result.state = "unavailable"
    assert all("score" not in field.name for cls in (
        model.ControlTowerReadModel, model.ShipmentAttentionItem, model.DisplayReason) for field in fields(cls))


def test_unauthorized_shipments_do_not_change_cursor_or_order_and_are_not_evaluated(tower, monkeypatch):
    shipments = [tower.shipment()[0] for _ in range(3)]
    mapping = {s.id: (reason(str(s.id)),) for s in shipments}
    stub(monkeypatch, mapping)
    calls = []
    original = sources.evaluate_bounded_sources
    def track(actor, contexts, **kw):
        calls.extend(c.shipment_id for c in contexts)
        return original(actor, contexts, **kw)
    monkeypatch.setattr(sources, "evaluate_bounded_sources", track)
    before = read(tower.a, page_size=1)
    other, _ = tower.shipment(owner=tower.b)
    foreign, _ = tower.shipment(owner=tower.foreign, tenant=tower.foreign_org)
    mapping[other.id] = mapping[foreign.id] = (reason("hidden", level=Level.URGENT),)
    after = read(tower.a, page_size=1)
    assert before == after
    assert other.id not in calls and foreign.id not in calls
    continuation = read(tower.a, page_size=1, cursor=before.page.next_cursor)
    assert continuation.items[0] != before.items[0]
    raw = base64.urlsafe_b64decode(before.page.next_cursor + "=" * (-len(before.page.next_cursor) % 4))
    assert all(s.public_id.encode() not in raw for s in (*shipments, other, foreign))


def test_cursor_bound_to_actor_and_query_while_data_changes_are_query_time_views(tower, monkeypatch):
    shipments = [tower.shipment()[0] for _ in range(3)]
    mapping = {s.id: (reason(str(s.id)),) for s in shipments}
    stub(monkeypatch, mapping)
    cursor = read(tower.a, page_size=1).page.next_cursor
    for actor, size, token in ((tower.admin, 1, cursor), (tower.a, 2, cursor),
                               (tower.a, 1, "invalid"), (tower.a, 1, cursor[:-4]+"AAAA")):
        with pytest.raises(model.ControlTowerCursorInvalid):
            read(actor, page_size=size, cursor=token)
    mapping[shipments[-1].id] = (reason("new", level=Level.URGENT),)
    changed = read(tower.a, page_size=1, cursor=cursor)
    assert changed.state == "complete"
    assert changed.page.offset == 1


@pytest.mark.parametrize("family", ["active_execution", "open_work", "readiness"])
def test_source_failure_never_discloses_partial_or_empty_success(attention, monkeypatch, family):
    attention.execution()
    def fail(*args, **kw):
        raise sources.ControlTowerSourceFailure(family)
    reader = {"active_execution": "_active_execution", "open_work": "_open_work", "readiness": "_readiness"}[family]
    monkeypatch.setattr(sources, reader, fail)
    result = read(attention.tower.a)
    assert result.state == "unavailable" and result.notice == UNAVAILABLE_MESSAGE
    assert result.items == () and result.empty_message is None and result.page.next_cursor is None
    assert family not in repr(asdict(result)) and PRIVATE not in repr(asdict(result))


def test_direct_readiness_not_applicable_and_empty_complete(tower):
    tower.shipment(source="direct")
    result = read(tower.a)
    assert result.state == "complete" and result.empty_message == EMPTY_MESSAGE


@pytest.mark.parametrize("source", ["direct", "accepted_quote"])
def test_request_or_owner_mutation_before_composition_cannot_transfer_scope(tower, source):
    from backend.services.control_tower_scope import governed_summary_scope

    shipment, request = tower.shipment(source=source)
    if request:
        request.assigned_to = tower.b.id
        db.session.commit()
    else:
        shipment.primary_responsible_expert_id = tower.b.id
        with pytest.raises(ValueError, match="responsible Expert is immutable"):
            db.session.commit()
        db.session.rollback()
    assert {row.shipment_id for row in governed_summary_scope({"id": tower.a.id})} == {
        shipment.id
    }
    assert governed_summary_scope({"id": tower.b.id}) == ()


@pytest.mark.parametrize("revocation", ["request_assignment", "membership", "persona", "owner_name"])
def test_revocation_during_composition_fails_closed(attention, monkeypatch, revocation):
    original = sources._readiness
    def revoke(*args, **kw):
        result = original(*args, **kw)
        if revocation == "request_assignment":
            attention.request.assigned_to = attention.tower.b.id
        elif revocation == "membership":
            attention.tower.am.is_active = False
        elif revocation == "persona":
            attention.tower.a.authority = "PLATFORM_ADMIN"
        else:
            attention.tower.a.full_name = "changed"
        db.session.commit()
        return result
    attention.execution()
    monkeypatch.setattr(sources, "_readiness", revoke)
    if revocation == "request_assignment":
        assert len(read(attention.tower.a).items) == 1
        assert read(attention.tower.b).items == ()
        return
    with pytest.raises(ControlTowerScopeDenied):
        read(attention.tower.a)


def test_earlier_item_revalidated_after_later_shipment_evaluation(tower, monkeypatch):
    first, request = tower.shipment()
    second, _ = tower.shipment()
    def adapter(actor, contexts, **kw):
        for context in contexts:
            if context.shipment_id == second.id:
                request.assigned_to = tower.b.id
                db.session.commit()
            yield context, (reason(str(context.shipment_id)),)
    monkeypatch.setattr(sources, "evaluate_bounded_sources", adapter)
    result = read(tower.a)
    assert result.state == "complete" and len(result.items) == 2
    assert read(tower.b).items == ()


def test_platform_denied_and_invalid_responsibility_never_empty(tower):
    shipment, request = tower.shipment()
    with pytest.raises(ControlTowerScopeDenied):
        read(tower.platform)
    db.session.execute(update(OperationalShipment).where(
        OperationalShipment.id == shipment.id
    ).values(primary_responsible_expert_id=tower.foreign.id))
    db.session.commit()
    with pytest.raises(ControlTowerResponsibilityInvariant):
        read(tower.admin)


def test_minimal_presentation_strips_all_source_provenance_and_finance(attention):
    attention.execution(label="هزینه حمل")
    attention.work(kind="REPLAN_REQUIRED", severity="critical")
    attention.requirement(family="FINANCE", title="هزینه حمل")
    result = read(attention.tower.admin)
    output = repr(asdict(result))
    for forbidden in (PRIVATE, "revenue", "cost", "margin", "FX", "assignee", "audit", "enrichment",
                      "source_identity", "source_severity", "WorkItem", "Situation", "OIP", "MDPM",
                      "CHECKPOINT_OVERDUE", "REPLAN_REQUIRED", "requirement_public_id", "هزینه"):
        assert forbidden not in output
    assert result.items[0].owner_name == attention.tower.a.full_name


def test_read_only_and_route_queries_bounded_to_authorized_shipments(attention):
    attention.execution()
    add_leg(attention)
    attention.tower.shipment(owner=attention.tower.foreign, tenant=attention.tower.foreign_org)
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append((statement.lower(), parameters))
    event.listen(db.engine, "before_cursor_execute", capture)
    try:
        assert read(attention.tower.a).state == "complete"
    finally:
        event.remove(db.engine, "before_cursor_execute", capture)
    assert all(sql.lstrip().split()[0] not in {"insert", "update", "delete"} for sql, _ in statements)
    route_sql = [(sql, params) for sql, params in statements if "from route_plan" in sql and " in (" in sql]
    assert len(route_sql) == 1
    assert attention.shipment.id in route_sql[0][1]


def test_batch_base_reads_are_bounded_once_per_family_not_per_shipment(tower):
    shipments = [tower.shipment(source="direct")[0] for _ in range(4)]
    tower.shipment(source="direct", owner=tower.b)
    tower.shipment(source="direct", owner=tower.foreign, tenant=tower.foreign_org)
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append((statement.lower(), parameters))
    event.listen(db.engine, "before_cursor_execute", capture)
    try:
        assert read(tower.a).empty_message == EMPTY_MESSAGE
    finally:
        event.remove(db.engine, "before_cursor_execute", capture)
    for family in ("operational_delay", "operational_exception", "operational_work_item"):
        queries = [(sql, parameters) for sql, parameters in statements if f"from {family} \n" in sql]
        assert len(queries) == 1
        sql, parameters = queries[0]
        assert "organization_id =" in sql and "operational_shipment_id in" in sql
        assert set(parameters[1:5]) == {s.id for s in shipments}


def test_composition_request_owner_route_and_tracking_queries_do_not_scale_per_row(
    tower, monkeypatch
):
    rows = [tower.shipment()[0]]
    mapping = {rows[0].id: (reason("one"),)}
    stub(monkeypatch, mapping)

    def count_queries():
        statements = []

        def capture(conn, cursor, statement, parameters, context, many):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", capture)
        try:
            result = read(tower.a)
            assert len(result.items) == len(rows)
        finally:
            event.remove(db.engine, "before_cursor_execute", capture)
        return len(statements)

    one = count_queries()
    for index in range(2, 11):
        shipment, _ = tower.shipment()
        rows.append(shipment)
        mapping[shipment.id] = (reason(str(index)),)
    many = count_queries()
    assert many <= one + 3


def test_batch_readiness_queries_do_not_scale_per_accepted_quote(attention):
    definition = DocumentDefinition(
        code="CT-BATCH-READINESS",
        title="بارنامه",
        allowed_formats='["pdf"]',
        max_file_size_bytes=1000,
    )
    db.session.add(definition)
    db.session.flush()

    def add_requirement(shipment, milestone):
        db.session.add(OperationalDocumentRequirement(
            organization_id=attention.tower.org.id,
            operational_shipment_id=shipment.id,
            document_definition_id=definition.id,
            requirement_level="CONDITIONAL",
            applicability_state="UNRESOLVED",
            target_milestone_type=milestone.milestone_type,
            target_status="READY",
            created_by_user_id=attention.tower.a.id,
        ))

    add_requirement(attention.shipment, attention.milestone)
    db.session.commit()

    def count_queries(expected):
        statements = []

        def capture(conn, cursor, statement, parameters, context, many):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", capture)
        try:
            result = read(attention.tower.a)
            assert len(result.items) == expected
        finally:
            event.remove(db.engine, "before_cursor_execute", capture)
        return len(statements)

    one = count_queries(1)
    for index in range(2, 11):
        shipment, _ = attention.tower.shipment()
        plan = RoutePlan(
            operational_shipment_id=shipment.id,
            created_by_user_id=attention.tower.a.id,
        )
        db.session.add(plan)
        db.session.flush()
        checkpoint = OperationalCheckpoint(
            route_plan_id=plan.id,
            sequence_number=1,
            checkpoint_type="border_entry",
            canonical_location_id=attention.location.id,
            planned_arrival_at=NOW,
            created_by_user_id=attention.tower.a.id,
        )
        db.session.add(checkpoint)
        db.session.flush()
        milestone = Milestone(
            organization_id=attention.tower.org.id,
            operational_shipment_id=shipment.id,
            route_plan_id=plan.id,
            checkpoint_id=checkpoint.id,
            milestone_type="ARRIVAL",
            sequence=1,
            lifecycle_status="PENDING",
        )
        db.session.add(milestone)
        db.session.flush()
        add_requirement(shipment, milestone)
    db.session.commit()

    many = count_queries(10)
    assert many <= one + 3


def test_batch_rejects_forged_or_revoked_lineage_before_source_queries(attention):
    from backend.services.control_tower_scope import governed_summary_scope
    contexts = governed_summary_scope(attention.actor)
    forged = (replace(contexts[0], organization_id=attention.tower.foreign_org.id),)
    with pytest.raises(ControlTowerScopeDenied):
        sources.evaluate_bounded_sources(attention.actor, forged, at=NOW)
    attention.request.assigned_to = attention.tower.b.id
    db.session.commit()
    assert sources.evaluate_bounded_sources(attention.actor, contexts, at=NOW)
    attention.tower.am.is_active = False
    db.session.commit()
    with pytest.raises(ControlTowerScopeDenied):
        sources.evaluate_bounded_sources(attention.actor, contexts, at=NOW)


def test_batch_query_failure_and_scope_system_failure_are_unavailable(tower, monkeypatch):
    tower.shipment()
    def fail(*args, **kw):
        raise RuntimeError(PRIVATE)
    monkeypatch.setattr(sources, "_all", fail)
    assert read(tower.a).state == "unavailable"
    monkeypatch.setattr(model, "governed_summary_scope", fail)
    result = read(tower.a)
    assert result.state == "unavailable" and result.empty_message is None
    assert PRIVATE not in repr(result)


def test_scope_query_row_order_does_not_change_completion_or_pagination(tower, monkeypatch):
    shipments = [tower.shipment()[0] for _ in range(3)]
    stub(monkeypatch, {s.id: (reason(str(s.id)),) for s in shipments})
    original = model.governed_summary_scope
    calls = []
    def reorder(actor):
        contexts = original(actor)
        calls.append(None)
        return tuple(reversed(contexts)) if len(calls) % 2 == 0 else contexts
    monkeypatch.setattr(model, "governed_summary_scope", reorder)
    result = read(tower.a, page_size=1)
    assert result.state == "complete" and result.page.next_cursor
    next_page = read(tower.a, page_size=1, cursor=result.page.next_cursor)
    assert next_page.items[0] != result.items[0]
