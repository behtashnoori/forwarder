"""Slice 2: bounded source truth, Persian semantics, provenance and firewalls."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import event, text, update

from backend.extensions import db
from backend.tests.test_control_tower_scope import tower  # noqa: F401
from backend.models import CaseDocumentFile, CaseDocumentRequirement, DocumentDefinition, DocumentDefinitionStage, ShipmentRequest
from backend.mdpm_models import ArtifactAssociation, DocumentAssessment, OperationalDocumentRequirement, TransitionOverride
from backend.oip_models import OipAttentionProjection, OipFactReference, OipSignal, OipSituation, OipSituationEvidence, OipThresholdPolicy
from backend.operational_models import (
    CanonicalLocation, DelayReason, ExceptionReason, Milestone, OperationalCheckpoint,
    OperationalDelay, OperationalException, OperationalWorkItem, RoutePlan,
)
from backend.services import control_tower_sources as sources, oip_service as oip
from backend.services.control_tower_scope import ControlTowerScopeDenied, governed_summary_scope
from backend.services.control_tower_translation import AttentionLevel as Level, Semantic, safe_display_label, translate, utc

NOW = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
PRIVATE = "PRIVATE revenue=999 cost=42 margin=957 FX=USD audit owner=secret"
ADAPTERS = (sources.evaluate_active_execution, sources.evaluate_open_work, sources.evaluate_readiness)


@pytest.fixture()
def attention(tower):
    shipment, request = tower.shipment()
    plan = RoutePlan(operational_shipment_id=shipment.id, created_by_user_id=tower.a.id)
    location = CanonicalLocation(source_type="city", source_id=1, location_type="city", display_name="تهران")
    db.session.add_all([plan, location])
    db.session.flush()
    checkpoint = OperationalCheckpoint(route_plan_id=plan.id, sequence_number=1,
        checkpoint_type="border_entry", canonical_location_id=location.id,
        planned_arrival_at=NOW - timedelta(days=2), created_by_user_id=tower.a.id, notes=PRIVATE)
    db.session.add(checkpoint)
    db.session.flush()
    milestone = Milestone(organization_id=tower.org.id, operational_shipment_id=shipment.id,
        route_plan_id=plan.id, checkpoint_id=checkpoint.id, milestone_type="ARRIVAL", sequence=1,
        planned_at=NOW - timedelta(days=2), milestone_type_snapshot={"fa_name": "ورود", "financial": PRIVATE})
    db.session.add(milestone)
    db.session.commit()
    actor = {"id": tower.a.id}
    context, = governed_summary_scope(actor)

    def execution(exception=False, label="خرابی وسیله نقلیه", resolved=False):
        reason_type = ExceptionReason if exception else DelayReason
        model = OperationalException if exception else OperationalDelay
        reason = reason_type(organization_id=tower.org.id, immutable_code=f"reason-{exception}-{label}",
            fa_name=label, en_name=PRIVATE, definition=PRIVATE,
            created_by_user_id=tower.a.id, updated_by_user_id=tower.a.id)
        db.session.add(reason)
        db.session.flush()
        field = "occurred_at" if exception else "started_at"
        row = model(organization_id=tower.org.id, operational_shipment_id=shipment.id,
            reason_id=reason.id, created_by_user_id=tower.a.id, note=PRIVATE,
            resolved_at=NOW if resolved else None, **{field: NOW - timedelta(hours=2)})
        db.session.add(row)
        db.session.commit()
        return row, reason

    def work(kind="CHECKPOINT_OVERDUE", severity="warning", **changes):
        links = {"milestone_id": milestone.id} if kind == "OVERDUE_MILESTONE" else {
            "route_plan_id": plan.id, "checkpoint_id": checkpoint.id}
        row = OperationalWorkItem(organization_id=tower.org.id, operational_shipment_id=shipment.id,
            work_type=kind, severity=severity, reason=PRIVATE, assignee_user_id=tower.b.id,
            due_at=NOW if kind == "ROUTE_DEPENDENCY_BLOCKED" else milestone.planned_at,
            detected_at=NOW - timedelta(hours=1), **links)
        for key, value in changes.items():
            setattr(row, key, value)
        db.session.add(row)
        db.session.commit()
        return row

    def requirement(level="REQUIRED", title="بارنامه", family=None):
        definition = DocumentDefinition(code=f"CT-{level}-{title}", title=title,
            family_code=family, allowed_formats='["pdf"]', max_file_size_bytes=1000, description=PRIVATE)
        db.session.add(definition)
        db.session.flush()
        req = OperationalDocumentRequirement(organization_id=tower.org.id,
            operational_shipment_id=shipment.id, document_definition_id=definition.id,
            requirement_level=level, applicability_state="UNRESOLVED" if level == "CONDITIONAL" else "APPLICABLE",
            target_milestone_type="ARRIVAL", target_status="READY", created_by_user_id=tower.a.id)
        db.session.add(req)
        db.session.commit()
        return req, definition

    return SimpleNamespace(tower=tower, shipment=shipment, request=request, plan=plan,
        checkpoint=checkpoint, milestone=milestone, location=location, actor=actor,
        context=context, execution=execution, work=work, requirement=requirement)


def _read(adapter, env):
    return adapter(env.actor, env.context, at=NOW)


def _observe(env, row, *, exception=False, work=False, overdue=False, severity="HIGH", urgency="HIGH"):
    if work:
        dimensions = {"work_type": row.work_type, "milestone_id": row.milestone_id,
                      "checkpoint_id": row.checkpoint_id, "route_plan_id": row.route_plan_id}
        typ = "NEXT_MILESTONE_OVERDUE" if overdue else row.work_type
        source_type = "OperationalMilestoneDue" if overdue else "OperationalWorkItem"
        key = env.milestone.public_id if overdue else f"owi-{row.id}"
        version = env.milestone.version if overdue else row.version
        occurred, due = utc(row.detected_at), utc(row.due_at)
    else:
        typ = "ACTIVE_DELAY_OR_EXCEPTION"
        source_type = "OperationalException" if exception else "OperationalDelay"
        key, version = row.public_id, row.version
        occurred, due = utc(row.occurred_at if exception else row.started_at), None
        dimensions = {"source_type": source_type, "source_public_id": key}
    kwargs = dict(organization_id=env.tower.org.id, subject_public_id=env.shipment.public_id,
        dimensions=dimensions, source_public_id=key, source_version=version,
        occurred_at=occurred, due_at=due, calculated_at=NOW)
    if overdue:
        policy = OipThresholdPolicy(organization_id=env.tower.org.id, signal_type=typ,
            scope_type="ENTERPRISE", scope_public_id="ENTERPRISE", value=1, unit="HOUR", version=1,
            authority="approved", source="test", effective_from=NOW-timedelta(days=10),
            created_by_user_id=env.tower.a.id, updated_by_user_id=env.tower.a.id)
        db.session.add(policy)
        db.session.flush()
        result = oip.evaluate_next_milestone_overdue(project_public_id=None, lifecycle_status="PENDING",
            due_source="RUNTIME_OPERATIONAL_WORK_ITEM_DUE", **kwargs)
    else:
        result = oip.observe(situation_type=typ, subject_type="SHIPMENT", source_domain="OPERATIONAL_EXECUTION",
            source_type=source_type, severity=severity, urgency=urgency, work_item_id=row.id if work else None,
            evidence={"private": PRIVATE}, **kwargs)
    db.session.commit()
    return db.session.scalar(db.select(OipSituation).where(OipSituation.public_id == result["public_id"]))


def _assert_minimal(reason):
    output = repr(asdict(reason))
    for forbidden in (PRIVATE, "revenue", "cost", "margin", "FX", "assignee", "file", "storage", "audit", "evidence"):
        assert forbidden not in output
    for internal in ("WorkItem", "Situation", "OIP", "MDPM", "CHECKPOINT_OVERDUE", "OVERDUE_MILESTONE"):
        assert internal not in reason.title + reason.explanation


def test_active_and_resolved_delay_specific_label_and_no_notes(attention):
    row, _ = attention.execution()
    reason, = _read(sources.evaluate_active_execution, attention)
    assert reason.semantic == Semantic.ACTIVE_DELAY
    assert reason.attention_level == Level.FOLLOW_UP
    assert "خرابی وسیله نقلیه" in reason.explanation
    assert reason.time_context[0].kind == "delay_start"
    _assert_minimal(reason)
    row.resolved_at = NOW
    db.session.commit()
    assert _read(sources.evaluate_active_execution, attention) == ()


def test_active_exception_specific_safe_title(attention):
    attention.execution(exception=True)
    reason, = _read(sources.evaluate_active_execution, attention)
    assert reason.title == "خرابی وسیله نقلیه هنوز برطرف نشده است"
    assert reason.attention_level == Level.FOLLOW_UP
    assert reason.time_context[0].kind == "exception_occurrence"
    _assert_minimal(reason)


@pytest.mark.parametrize("label", ["هزینه حمل ۹۹۹ دلار", "PRIVATE margin", "<script>خرابی</script>"])
def test_unsafe_reason_display_has_nonrevealing_fallback(attention, label):
    attention.execution(exception=True, label=label)
    reason, = _read(sources.evaluate_active_execution, attention)
    assert reason.title == "یک مشکل عملیاتی هنوز برطرف نشده است"
    assert label not in repr(asdict(reason))


def test_oip_high_high_enriches_one_existing_reason(attention):
    row, _ = attention.execution()
    _observe(attention, row)
    reason, = _read(sources.evaluate_active_execution, attention)
    assert reason.attention_level == Level.URGENT
    assert len(reason.enrichment) == 1
    assert reason.source_identity.key == row.public_id
    _assert_minimal(reason)
    row.resolved_at = NOW
    db.session.commit()
    assert _read(sources.evaluate_active_execution, attention) == ()  # OIP alone does nothing


@pytest.mark.parametrize("damage", ["version", "evidence", "signal", "watermark", "projection", "dimensions", "tenant", "shipment", "fact_tenant", "fact_shipment", "policy", "terminal"])
def test_stale_unlinked_foreign_oip_ignored(attention, damage):
    row, _ = attention.execution()
    situation = _observe(attention, row)
    fact = OipFactReference.query.one()
    signal = OipSignal.query.one()
    projection = db.session.get(OipAttentionProjection, situation.id)
    if damage == "version":
        db.session.execute(update(OperationalDelay).where(OperationalDelay.id == row.id).values(version=2))
    elif damage == "evidence":
        OipSituationEvidence.query.one().is_current = False
    elif damage == "signal":
        signal.active = False
    elif damage == "watermark":
        signal.source_watermark = "stale"
    elif damage == "projection":
        projection.projection_version = "old"
    elif damage == "dimensions":
        situation.identity_dimensions = {"other": "source"}
    elif damage == "tenant":
        situation.organization_id = attention.tower.foreign_org.id
    elif damage == "shipment":
        situation.subject_public_id = "other-shipment"
    elif damage == "fact_tenant":
        fact.organization_id = attention.tower.foreign_org.id
    elif damage == "fact_shipment":
        fact.subject_public_id = "other-shipment"
    elif damage == "policy":
        situation.policy_version = "old"
    else:
        situation.status = "SNOOZED"
        situation.snoozed_until = NOW + timedelta(days=1)
    db.session.commit()
    reason, = _read(sources.evaluate_active_execution, attention)
    assert reason.attention_level == Level.FOLLOW_UP
    assert reason.enrichment == ()


@pytest.mark.parametrize("kind,severity,expected", [
    ("CHECKPOINT_OVERDUE", "warning", Level.FOLLOW_UP),
    ("ROUTE_DEPENDENCY_BLOCKED", "critical", Level.URGENT),
    ("REPLAN_REQUIRED", "critical", Level.URGENT),
    ("OVERDUE_MILESTONE", "warning", Level.FOLLOW_UP),
])
def test_supported_work_meaning_level_and_time(attention, kind, severity, expected):
    attention.work(kind, severity)
    reason, = _read(sources.evaluate_open_work, attention)
    assert reason.attention_level == expected
    assert (len(reason.time_context) == 1) == (kind == "ROUTE_DEPENDENCY_BLOCKED")
    if kind == "CHECKPOINT_OVERDUE":
        assert "نقطه مرزی تهران" in reason.title
    if kind == "OVERDUE_MILESTONE":
        assert "تأیید ورود" in reason.title
    _assert_minimal(reason)


@pytest.mark.parametrize("damage", ["closed", "superseded", "cancelled_checkpoint", "verified", "completed", "unsupported", "missing_link"])
def test_ineligible_work_excluded(attention, damage):
    kind = "OVERDUE_MILESTONE" if damage in {"verified", "completed"} else "CHECKPOINT_OVERDUE"
    row = attention.work(kind)
    if damage == "closed":
        row.status = "resolved"
    elif damage == "superseded":
        attention.plan.is_active = False
        attention.plan.status = "superseded"
    elif damage == "cancelled_checkpoint":
        attention.checkpoint.status = "cancelled"
    elif damage == "verified":
        attention.milestone.verification_state = "verified"
    elif damage == "completed":
        attention.milestone.lifecycle_status = "COMPLETED"
    elif damage == "unsupported":
        # Simulate future/unapproved type without changing the real schema.
        db.session.execute(text("PRAGMA ignore_check_constraints = ON"))
        row.work_type = "FUTURE_UNAPPROVED"
    else:
        row.checkpoint_id = 999999
    db.session.commit()
    if damage == "unsupported":
        db.session.execute(text("PRAGMA ignore_check_constraints = OFF"))
    assert _read(sources.evaluate_open_work, attention) == ()


def test_work_due_mismatch_omitted_and_severity_not_generalized(attention):
    attention.work(severity="critical", due_at=NOW-timedelta(days=5))
    reason, = _read(sources.evaluate_open_work, attention)
    assert reason.attention_level == Level.FOLLOW_UP
    assert [t.kind for t in reason.time_context] == ["work_open"]


def test_dependency_synthetic_due_never_promotes_high_oip(attention):
    row = attention.work("ROUTE_DEPENDENCY_BLOCKED", "warning")
    row.due_at = NOW - timedelta(minutes=1)
    db.session.commit()
    _observe(attention, row, work=True, severity="HIGH", urgency="HIGH")
    reason, = _read(sources.evaluate_open_work, attention)
    assert reason.attention_level == Level.FOLLOW_UP
    assert reason.enrichment and not reason.enrichment[0].promotes_urgent
    assert [t.kind for t in reason.time_context] == ["work_open"]


def test_governed_overdue_enrichment_and_policy_revocation(attention):
    row = attention.work("OVERDUE_MILESTONE")
    _observe(attention, row, work=True, overdue=True)
    reason, = _read(sources.evaluate_open_work, attention)
    assert reason.attention_level == Level.URGENT
    OipThresholdPolicy.query.one().is_active = False
    db.session.commit()
    reason, = _read(sources.evaluate_open_work, attention)
    assert reason.attention_level == Level.FOLLOW_UP
    assert reason.enrichment == ()


def test_checkpoint_verified_oip_urgency_and_no_duplicate_reason(attention):
    row = attention.work()
    _observe(attention, row, work=True, severity="MEDIUM", urgency="HIGH")
    reason, = _read(sources.evaluate_open_work, attention)
    assert reason.attention_level == Level.URGENT
    assert len(reason.enrichment) == 1
    assert reason.source_identity.key == str(row.id)


@pytest.mark.parametrize("levels,expected", [(["REQUIRED"], Level.FOLLOW_UP), (["CONDITIONAL"], Level.REVIEW), (["REQUIRED", "CONDITIONAL"], Level.FOLLOW_UP)])
def test_readiness_blocker_uncertainty_and_mixed_one_transition(attention, levels, expected):
    for level in levels:
        attention.requirement(level, title="بارنامه" if level == "REQUIRED" else "مجوز عبور")
    reason, = _read(sources.evaluate_readiness, attention)
    assert reason.attention_level == expected
    assert "بارنامه" in reason.explanation or "مجوز عبور" in reason.explanation
    assert [t.kind for t in reason.time_context] == ["evaluated"]
    assert reason.time_context[0].label == "بررسی‌شده در"
    _assert_minimal(reason)


@pytest.mark.parametrize("family,stage", [("FINANCE", False), (None, True)])
def test_readiness_financial_catalog_label_suppressed(attention, family, stage):
    _, definition = attention.requirement(title="تسویه", family=family)
    if stage:
        db.session.add(DocumentDefinitionStage(document_definition_id=definition.id, stage_code="PAYMENT_FINANCE"))
        db.session.commit()
    reason, = _read(sources.evaluate_readiness, attention)
    assert "تسویه" not in reason.explanation
    assert reason.attention_level == Level.FOLLOW_UP


def _artifact(env, req, definition):
    case = CaseDocumentRequirement(operational_organization_id=env.tower.org.id,
        shipment_request_id=env.request.id, source_definition_id=definition.id, title="بارنامه",
        source_definition_code=definition.code, source_definition_revision=1,
        is_required=True, sort_order=0,
        allowed_formats='["pdf"]', max_file_size_bytes=1000, max_active_file_count=1)
    db.session.add(case)
    db.session.flush()
    file = CaseDocumentFile(operational_organization_id=env.tower.org.id, shipment_request_id=env.request.id,
        case_requirement_id=case.id, original_filename=PRIVATE, safe_download_filename=PRIVATE,
        storage_key=PRIVATE, canonical_extension="pdf", detected_mime_type="application/pdf",
        file_size_bytes=10, sha256_hash="a"*64, version_number=1)
    db.session.add(file)
    db.session.flush()
    assoc = ArtifactAssociation(organization_id=env.tower.org.id, requirement_id=req.id,
        document_file_id=file.id, artifact_version=1, reason=PRIVATE, associated_by_user_id=env.tower.a.id)
    db.session.add(assoc)
    db.session.flush()
    assessment = DocumentAssessment(organization_id=env.tower.org.id, association_id=assoc.id,
        decision="REJECTED", reason=PRIVATE, actor_user_id=env.tower.a.id)
    db.session.add(assessment)
    db.session.commit()
    return file, assoc, assessment


def test_readiness_existing_artifact_decision_only_and_fresh_state(attention):
    req, definition = attention.requirement()
    file, assoc, assessment = _artifact(attention, req, definition)
    reason, = _read(sources.evaluate_readiness, attention)
    assert "رد شده" in reason.explanation
    _assert_minimal(reason)
    # Update persistence behind retained ORM relationships: no stale decision.
    db.session.execute(update(DocumentAssessment).where(DocumentAssessment.id == assessment.id).values(decision="APPROVED"))
    db.session.commit()
    assert _read(sources.evaluate_readiness, attention) == ()


@pytest.mark.parametrize("damage", ["association", "artifact", "assessment"])
def test_foreign_readiness_link_fails_evaluation_without_disclosure(attention, damage):
    req, definition = attention.requirement()
    file, assoc, assessment = _artifact(attention, req, definition)
    if damage == "artifact":
        file.operational_organization_id = attention.tower.foreign_org.id
    else:
        (assoc if damage == "association" else assessment).organization_id = attention.tower.foreign_org.id
    db.session.commit()
    with pytest.raises(sources.ControlTowerSourceFailure) as failed:
        _read(sources.evaluate_readiness, attention)
    assert PRIVATE not in str(failed.value)


def test_readiness_optional_override_and_direct_not_applicable(attention):
    req, _ = attention.requirement("OPTIONAL")
    assert _read(sources.evaluate_readiness, attention) == ()
    req.requirement_level = "REQUIRED"
    override = TransitionOverride(organization_id=attention.tower.org.id,
        operational_shipment_id=attention.shipment.id, requirement_id=req.id,
        milestone_id=attention.milestone.id, target_status="READY", actor_user_id=attention.tower.a.id,
        authority="approved", evidence_reference=PRIVATE, reason=PRIVATE)
    db.session.add(override)
    db.session.commit()
    assert _read(sources.evaluate_readiness, attention) == ()
    direct, _ = attention.tower.shipment(source="direct")
    context = next(c for c in governed_summary_scope(attention.actor) if c.shipment_id == direct.id)
    assert sources.evaluate_readiness(attention.actor, context, at=NOW) == ()


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_request_reassignment_preserves_context_but_owner_revocation_denies(attention, adapter):
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.lower())
    db.session.execute(update(ShipmentRequest).where(ShipmentRequest.id == attention.request.id).values(assigned_to=attention.tower.b.id))
    db.session.commit()
    event.listen(db.engine, "before_cursor_execute", capture)
    try:
        _read(adapter, attention)
    finally:
        event.remove(db.engine, "before_cursor_execute", capture)
    attention.tower.am.is_active = False
    db.session.commit()
    with pytest.raises(ControlTowerScopeDenied):
        _read(adapter, attention)


def test_revocation_during_evaluation_fails_before_disclosure(attention, monkeypatch):
    original = sources._active_execution
    def revoked(actor, context, at):
        result = original(actor, context, at)
        attention.tower.am.is_active = False
        db.session.commit()
        return result
    monkeypatch.setattr(sources, "_active_execution", revoked)
    with pytest.raises(ControlTowerScopeDenied):
        _read(sources.evaluate_active_execution, attention)


def test_admin_summary_without_grants_platform_denied_and_foreign_sources(attention):
    row, _ = attention.execution()
    work = attention.work()
    requirement, _ = attention.requirement()
    actor = {"id": attention.tower.admin.id}
    context, = governed_summary_scope(actor)
    for adapter in ADAPTERS:
        assert adapter(actor, context, at=NOW)
        with pytest.raises(ControlTowerScopeDenied):
            adapter({"id": attention.tower.platform.id}, context, at=NOW)
    row.organization_id = attention.tower.foreign_org.id
    work.organization_id = attention.tower.foreign_org.id
    requirement.organization_id = attention.tower.foreign_org.id
    db.session.commit()
    for adapter in ADAPTERS:
        assert _read(adapter, attention) == ()
    assert attention.tower.adminm.permissions == ["operational_shipment.read"]


@pytest.mark.parametrize("adapter,reader,source", [
    (sources.evaluate_active_execution, "_active_execution", "active_execution"),
    (sources.evaluate_open_work, "_open_work", "open_work"),
    (sources.evaluate_readiness, "_readiness", "readiness"),
])
def test_failure_is_never_successful_empty_and_is_opaque(attention, monkeypatch, adapter, reader, source):
    assert _read(adapter, attention) == ()
    def broken(*args):
        raise RuntimeError(PRIVATE)
    monkeypatch.setattr(sources, reader, broken)
    with pytest.raises(sources.ControlTowerSourceFailure) as failed:
        _read(adapter, attention)
    assert failed.value.source == source
    assert PRIVATE not in str(failed.value)


def test_read_only_bounded_queries_and_no_autoflush(attention):
    row, _ = attention.execution()
    attention.work()
    attention.requirement()
    _observe(attention, row)
    # A dirty unrelated object must not cause writes during summary evaluation.
    attention.location.display_name = "تغییر ذخیره نشده"
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append((statement.lower(), parameters))
    event.listen(db.engine, "before_cursor_execute", capture)
    try:
        for adapter in ADAPTERS:
            assert _read(adapter, attention)
    finally:
        event.remove(db.engine, "before_cursor_execute", capture)
    assert statements and all(s.lstrip().startswith("select") for s, _ in statements)
    for s, params in statements:
        if "from operational_delay" in s or "from operational_exception" in s or "from operational_work_item" in s:
            assert "operational_shipment_id =" in s and "organization_id =" in s
        if "from oip_situation" in s:
            assert "source_public_id =" in s and "subject_public_id =" in s and "organization_id =" in s


def test_translation_catalog_covers_all_semantics_and_rejects_protected_labels():
    assert len(Semantic) == 8
    for semantic in Semantic:
        title, explanation = translate(semantic)
        assert title and explanation and "WorkItem" not in title + explanation
    assert safe_display_label("  خرابی وسیله نقلیه  ") == "خرابی وسیله نقلیه"
    assert safe_display_label("پرداخت محرمانه") is None


def test_oip_enriches_only_matching_source_and_high_severity_alone_is_insufficient(attention):
    row, _ = attention.execution()
    other, _ = attention.execution(exception=True, label="مانع مسیر")
    _observe(attention, row, severity="HIGH", urgency="MEDIUM")
    reasons = _read(sources.evaluate_active_execution, attention)
    assert len(reasons) == 2
    assert all(r.attention_level == Level.FOLLOW_UP for r in reasons)
    assert next(r for r in reasons if r.source_identity.key == other.public_id).enrichment == ()
    _observe(attention, row)
    reasons = _read(sources.evaluate_active_execution, attention)
    assert next(r for r in reasons if r.source_identity.key == row.public_id).attention_level == Level.URGENT
    assert next(r for r in reasons if r.source_identity.key == other.public_id).attention_level == Level.FOLLOW_UP
