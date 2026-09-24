"""Organization-owned SLA rules and deterministic process evaluation.

Only code-defined, already meaningful processes are bindable. Rules are
prospective and commitments pin their effective rule version so history is not
rewritten by a later administration change.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text

from backend.extensions import db
from backend.operational_models import (
    OperationalAudit,
    OperationalException,
    OperationalOrganization,
    OperationalShipment,
    OperationalSlaCommitment,
    OperationalWorkItem,
    OrganizationSlaRule,
    utcnow,
)
from backend.services.operational_service import (
    OperationalError,
    organization_for_user,
)


PROCESS_DEFINITIONS = {
    "EXCEPTION_RESPONSE": {
        "label_fa": "رسیدگی به استثنای عملیاتی",
        "start_reference": "OperationalException.occurred_at",
        "completion_reference": "OperationalException.resolved_at",
        "responsibility": "SHIPMENT_TRANSPORT_EXPERT",
    },
    "ACTION_FOLLOW_UP": {
        "label_fa": "پیگیری اقدام عملیاتی",
        "start_reference": "OperationalWorkItem.created_at",
        "completion_reference": "OperationalWorkItem.resolved_at",
        "responsibility": "SHIPMENT_TRANSPORT_EXPERT",
    },
}
STATUS_RANK = {"BREACHED": 0, "WARNING": 1, "WITHIN": 2, "MET": 3}


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _admin_organization(user: dict[str, Any]) -> int:
    if (user.get("authority") or "").upper() != "ORGANIZATION_ADMIN":
        raise OperationalError(
            "FORBIDDEN_OPERATION",
            "Organization SLA management requires Organization Admin authority.",
            403,
        )
    return organization_for_user(int(user["id"]))


def process_catalog() -> list[dict[str, str]]:
    return [
        {"process_type": code, **definition}
        for code, definition in PROCESS_DEFINITIONS.items()
    ]


def _integer(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise OperationalError(
            "VALIDATION_FAILED",
            f"{field} must be an integer between {minimum} and {maximum}.",
            422,
        )
    return value


def _validated_rule_fields(payload: dict[str, Any], current=None) -> dict[str, Any]:
    process_type = payload.get("process_type", getattr(current, "process_type", None))
    if process_type not in PROCESS_DEFINITIONS:
        raise OperationalError(
            "UNSUPPORTED_SLA_PROCESS",
            "The requested process is not supported by the governed SLA catalog.",
            422,
        )
    name = str(payload.get("name", getattr(current, "name", "")) or "").strip()
    if not name or len(name) > 120:
        raise OperationalError(
            "VALIDATION_FAILED", "name must contain 1 to 120 characters.", 422
        )
    duration = _integer(
        payload.get("duration_minutes", getattr(current, "duration_minutes", None)),
        "duration_minutes",
        minimum=1,
        maximum=525600,
    )
    warning_value = payload.get(
        "warning_minutes", getattr(current, "warning_minutes", None)
    )
    warning = None
    if warning_value is not None:
        warning = _integer(
            warning_value,
            "warning_minutes",
            minimum=1,
            maximum=525599,
        )
        if warning >= duration:
            raise OperationalError(
                "VALIDATION_FAILED",
                "warning_minutes must be less than duration_minutes.",
                422,
            )
    active = payload.get("is_active", getattr(current, "is_active", True))
    if type(active) is not bool:
        raise OperationalError(
            "VALIDATION_FAILED", "is_active must be a boolean.", 422
        )
    return {
        "process_type": process_type,
        "name": name,
        "duration_minutes": duration,
        "warning_minutes": warning,
        "is_active": active,
    }


def _rule_snapshot(rule: OrganizationSlaRule) -> dict[str, Any]:
    definition = PROCESS_DEFINITIONS[rule.process_type]
    return {
        "public_id": rule.public_id,
        "process_type": rule.process_type,
        "name": rule.name,
        "duration_minutes": rule.duration_minutes,
        "warning_minutes": rule.warning_minutes,
        "is_active": rule.is_active,
        "effective_from": rule.effective_from.isoformat(),
        "version": rule.version,
        **definition,
    }


def serialize_rule(rule: OrganizationSlaRule) -> dict[str, Any]:
    return {
        **_rule_snapshot(rule),
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


def list_rules(user: dict[str, Any]) -> dict[str, Any]:
    org = _admin_organization(user)
    rows = db.session.scalars(
        select(OrganizationSlaRule)
        .where(OrganizationSlaRule.organization_id == org)
        .order_by(OrganizationSlaRule.process_type)
    ).all()
    configured = {row.process_type: serialize_rule(row) for row in rows}
    return {
        "catalog": process_catalog(),
        "rules": [configured[code] for code in PROCESS_DEFINITIONS if code in configured],
        "unconfigured_processes": [
            {"process_type": code, "label_fa": definition["label_fa"], "status_label": "SLA تعریف نشده"}
            for code, definition in PROCESS_DEFINITIONS.items()
            if code not in configured
        ],
    }


def create_rule(payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    org = _admin_organization(user)
    fields = _validated_rule_fields(payload)
    existing = db.session.scalar(
        select(OrganizationSlaRule).where(
            OrganizationSlaRule.organization_id == org,
            OrganizationSlaRule.process_type == fields["process_type"],
        )
    )
    if existing is not None:
        raise OperationalError(
            "SLA_RULE_ALREADY_EXISTS",
            "An SLA rule already exists for this organization process.",
            409,
        )
    now = utcnow()
    rule = OrganizationSlaRule(
        organization_id=org,
        effective_from=now,
        version=1,
        created_by_user_id=int(user["id"]),
        updated_by_user_id=int(user["id"]),
        created_at=now,
        updated_at=now,
        **fields,
    )
    db.session.add(rule)
    db.session.flush()
    db.session.add(
        OperationalAudit(
            organization_id=org,
            actor_user_id=int(user["id"]),
            action="organization_sla_rule.created",
            entity_type="OrganizationSlaRule",
            entity_id=rule.id,
            metadata_json={"after": _rule_snapshot(rule)},
        )
    )
    db.session.commit()
    return serialize_rule(rule)


def update_rule(
    public_id: str, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    org = _admin_organization(user)
    rule = db.session.scalar(
        select(OrganizationSlaRule)
        .where(
            OrganizationSlaRule.organization_id == org,
            OrganizationSlaRule.public_id == public_id,
        )
        .with_for_update()
    )
    if rule is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "SLA rule was not found.", 404)
    expected = payload.get("expected_version")
    if type(expected) is not int or expected != rule.version:
        raise OperationalError(
            "STALE_AGGREGATE_VERSION",
            "SLA rule was changed by another operation.",
            409,
        )
    if "process_type" in payload and payload["process_type"] != rule.process_type:
        raise OperationalError(
            "IMMUTABLE_PROCESS_TYPE", "SLA process type cannot be changed.", 422
        )
    # Catch up every source governed by the current version before advancing
    # its prospective effective boundary. A delayed scheduler therefore cannot
    # lose commitments merely because an administrator edits or disables a rule.
    now = utcnow()
    evaluate_organization(org, calculation_time=now)
    before = _rule_snapshot(rule)
    fields = _validated_rule_fields(payload, rule)
    for field, value in fields.items():
        setattr(rule, field, value)
    rule.effective_from = now
    rule.version += 1
    rule.updated_by_user_id = int(user["id"])
    rule.updated_at = now
    db.session.add(
        OperationalAudit(
            organization_id=org,
            actor_user_id=int(user["id"]),
            action="organization_sla_rule.updated",
            entity_type="OrganizationSlaRule",
            entity_id=rule.id,
            metadata_json={"before": before, "after": _rule_snapshot(rule)},
        )
    )
    db.session.commit()
    return serialize_rule(rule)


def rule_history(public_id: str, user: dict[str, Any]) -> list[dict[str, Any]]:
    org = _admin_organization(user)
    rule = db.session.scalar(
        select(OrganizationSlaRule).where(
            OrganizationSlaRule.organization_id == org,
            OrganizationSlaRule.public_id == public_id,
        )
    )
    if rule is None:
        raise OperationalError("RESOURCE_NOT_FOUND", "SLA rule was not found.", 404)
    rows = db.session.scalars(
        select(OperationalAudit)
        .where(
            OperationalAudit.organization_id == org,
            OperationalAudit.entity_type == "OrganizationSlaRule",
            OperationalAudit.entity_id == rule.id,
        )
        .order_by(OperationalAudit.recorded_at, OperationalAudit.id)
    ).all()
    return [
        {
            "action": row.action,
            "actor_user_id": row.actor_user_id,
            "occurred_at": row.recorded_at.isoformat(),
            "change": row.metadata_json,
        }
        for row in rows
    ]


def _lock_organization(organization_id: int) -> None:
    if db.session.get_bind().dialect.name == "postgresql":
        db.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"organization-sla:{organization_id}"},
        )


def _source_rows(rule: OrganizationSlaRule):
    effective = _aware(rule.effective_from)
    if rule.process_type == "EXCEPTION_RESPONSE":
        rows = db.session.scalars(
            select(OperationalException).where(
                OperationalException.organization_id == rule.organization_id,
                OperationalException.occurred_at >= effective,
            )
        ).all()
        return [
            (
                "OperationalException",
                row.public_id,
                row.version,
                row.operational_shipment_id,
                row.occurred_at,
                row.resolved_at,
            )
            for row in rows
        ]
    rows = db.session.scalars(
        select(OperationalWorkItem).where(
            OperationalWorkItem.organization_id == rule.organization_id,
            OperationalWorkItem.work_type == "FOLLOW_UP",
            OperationalWorkItem.created_at >= effective,
        )
    ).all()
    return [
        (
            "OperationalWorkItem",
            row.public_id,
            row.version,
            row.operational_shipment_id,
            row.created_at,
            row.resolved_at,
        )
        for row in rows
    ]


def _status(
    *, now: datetime, due_at: datetime, warning_at: datetime | None, completed_at: datetime | None
) -> str:
    if completed_at is not None:
        return "MET" if _aware(completed_at) <= due_at else "BREACHED"
    if now >= due_at:
        return "BREACHED"
    if warning_at is not None and now >= warning_at:
        return "WARNING"
    return "WITHIN"


def evaluate_organization(
    organization_id: int, *, calculation_time: datetime | None = None
) -> dict[str, Any]:
    """Discover new commitments and refresh every pinned commitment idempotently."""
    now = _aware(calculation_time or utcnow())
    organization = db.session.get(OperationalOrganization, organization_id)
    if organization is None or not organization.is_active:
        raise OperationalError(
            "RESOURCE_NOT_FOUND", "Operational organization was not found.", 404
        )
    _lock_organization(organization_id)
    rules = db.session.scalars(
        select(OrganizationSlaRule).where(
            OrganizationSlaRule.organization_id == organization_id
        )
    ).all()
    created = 0
    for rule in rules:
        if not rule.is_active or _aware(rule.effective_from) > now:
            continue
        for source_type, source_public_id, source_version, shipment_id, started, completed in _source_rows(rule):
            commitment = db.session.scalar(
                select(OperationalSlaCommitment).where(
                    OperationalSlaCommitment.organization_id == organization_id,
                    OperationalSlaCommitment.process_type == rule.process_type,
                    OperationalSlaCommitment.source_public_id == source_public_id,
                )
            )
            if commitment is not None:
                continue
            shipment = db.session.scalar(
                select(OperationalShipment).where(
                    OperationalShipment.id == shipment_id,
                    OperationalShipment.organization_id == organization_id,
                )
            )
            if shipment is None:
                raise OperationalError(
                    "SLA_SOURCE_INTEGRITY_FAILED",
                    "SLA source Shipment integrity could not be verified.",
                    409,
                )
            started_at = _aware(started)
            due_at = started_at + timedelta(minutes=rule.duration_minutes)
            warning_at = (
                due_at - timedelta(minutes=rule.warning_minutes)
                if rule.warning_minutes is not None
                else None
            )
            completed_at = _aware(completed) if completed is not None else None
            evaluation_status = _status(
                now=now,
                due_at=due_at,
                warning_at=warning_at,
                completed_at=completed_at,
            )
            snapshot = _rule_snapshot(rule)
            watermark = (
                f"{source_type}:{source_public_id}:{source_version}|"
                f"rule:{rule.public_id}:{rule.version}|status:{evaluation_status}"
            )
            commitment = OperationalSlaCommitment(
                organization_id=organization_id,
                rule_id=rule.id,
                rule_version=rule.version,
                process_type=rule.process_type,
                operational_shipment_id=shipment.id,
                responsible_user_id=shipment.primary_responsible_expert_id,
                source_type=source_type,
                source_public_id=source_public_id,
                source_version=source_version,
                started_at=started_at,
                warning_at=warning_at,
                due_at=due_at,
                completed_at=completed_at,
                evaluation_status=evaluation_status,
                evaluated_at=now,
                source_watermark=watermark,
                rule_snapshot=snapshot,
                explanation={
                    "status": evaluation_status,
                    "process_type": rule.process_type,
                    "process_label": PROCESS_DEFINITIONS[rule.process_type]["label_fa"],
                    "rule_public_id": rule.public_id,
                    "rule_version": rule.version,
                    "source_type": source_type,
                    "source_public_id": source_public_id,
                    "started_at": started_at.isoformat(),
                    "warning_at": warning_at.isoformat() if warning_at else None,
                    "due_at": due_at.isoformat(),
                    "completed_at": completed_at.isoformat() if completed_at else None,
                    "evaluated_at": now.isoformat(),
                    "clock": "ABSOLUTE_ELAPSED_UTC_MINUTES",
                },
                version=1,
                created_at=now,
                updated_at=now,
            )
            db.session.add(commitment)
            created += 1
    db.session.flush()

    source_maps = {
        "OperationalException": {
            row.public_id: row
            for row in db.session.scalars(
                select(OperationalException).where(
                    OperationalException.organization_id == organization_id
                )
            ).all()
        },
        "OperationalWorkItem": {
            row.public_id: row
            for row in db.session.scalars(
                select(OperationalWorkItem).where(
                    OperationalWorkItem.organization_id == organization_id,
                    OperationalWorkItem.work_type == "FOLLOW_UP",
                )
            ).all()
        },
    }
    changed = 0
    commitments = db.session.scalars(
        select(OperationalSlaCommitment)
        .where(OperationalSlaCommitment.organization_id == organization_id)
        .with_for_update()
    ).all()
    for commitment in commitments:
        source = source_maps[commitment.source_type].get(commitment.source_public_id)
        if source is None:
            raise OperationalError(
                "SLA_SOURCE_INTEGRITY_FAILED",
                "A pinned SLA source could not be verified.",
                409,
            )
        completed_at = _aware(source.resolved_at) if source.resolved_at else None
        status = _status(
            now=now,
            due_at=_aware(commitment.due_at),
            warning_at=_aware(commitment.warning_at) if commitment.warning_at else None,
            completed_at=completed_at,
        )
        watermark = (
            f"{commitment.source_type}:{commitment.source_public_id}:{source.version}|"
            f"rule:{commitment.rule_snapshot['public_id']}:{commitment.rule_version}|status:{status}"
        )
        material_change = (
            commitment.evaluation_status != status
            or commitment.source_version != source.version
            or commitment.completed_at != completed_at
            or commitment.source_watermark != watermark
        )
        commitment.source_version = source.version
        commitment.completed_at = completed_at
        commitment.evaluation_status = status
        commitment.evaluated_at = now
        commitment.source_watermark = watermark
        commitment.explanation = {
            **(commitment.explanation or {}),
            "status": status,
            "source_version": source.version,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "evaluated_at": now.isoformat(),
        }
        commitment.updated_at = now
        if material_change:
            commitment.version += 1
            changed += 1
    db.session.flush()
    return {
        "organization_id": organization_id,
        "calculated_at": now.isoformat(),
        "created_commitments": created,
        "changed_commitments": changed,
        "evaluated_commitments": len(commitments),
    }


def serialize_commitment(commitment: OperationalSlaCommitment) -> dict[str, Any]:
    return {
        "public_id": commitment.public_id,
        "process_type": commitment.process_type,
        "process_label": PROCESS_DEFINITIONS[commitment.process_type]["label_fa"],
        "status": commitment.evaluation_status,
        "rule": commitment.rule_snapshot,
        "source": {
            "type": commitment.source_type,
            "public_id": commitment.source_public_id,
            "version": commitment.source_version,
        },
        "responsible_user_id": commitment.responsible_user_id,
        "started_at": commitment.started_at.isoformat(),
        "warning_at": commitment.warning_at.isoformat() if commitment.warning_at else None,
        "due_at": commitment.due_at.isoformat(),
        "completed_at": commitment.completed_at.isoformat() if commitment.completed_at else None,
        "evaluated_at": commitment.evaluated_at.isoformat(),
        "explanation": commitment.explanation,
        "version": commitment.version,
    }


def shipment_status(
    shipment: OperationalShipment,
    *,
    allowed_source_types: set[str] | None = None,
) -> dict[str, Any]:
    if allowed_source_types is not None and not allowed_source_types:
        return {
            "status": "UNAVAILABLE",
            "status_label": "جزئیات SLA با دسترسی فعلی قابل نمایش نیست",
            "commitments": [],
        }
    commitments = db.session.scalars(
        select(OperationalSlaCommitment)
        .where(
            OperationalSlaCommitment.organization_id == shipment.organization_id,
            OperationalSlaCommitment.operational_shipment_id == shipment.id,
        )
        .order_by(OperationalSlaCommitment.due_at, OperationalSlaCommitment.id)
    ).all()
    if allowed_source_types is not None:
        commitments = [
            row for row in commitments if row.source_type in allowed_source_types
        ]
    if commitments:
        open_rows = [row for row in commitments if row.completed_at is None]
        cohort = open_rows or commitments
        overall = min(cohort, key=lambda row: STATUS_RANK[row.evaluation_status]).evaluation_status
        return {
            "status": overall,
            "status_label": {
                "WITHIN": "در محدوده SLA",
                "WARNING": "نزدیک به نقض SLA",
                "BREACHED": "SLA نقض شده",
                "MET": "SLA رعایت شده",
            }[overall],
            "commitments": [serialize_commitment(row) for row in commitments],
        }
    configured_rules = db.session.scalars(
        select(OrganizationSlaRule).where(
            OrganizationSlaRule.organization_id == shipment.organization_id,
            OrganizationSlaRule.is_active.is_(True),
            OrganizationSlaRule.effective_from <= utcnow(),
        )
    ).all()
    pending = False
    for rule in configured_rules:
        if (
            rule.process_type == "EXCEPTION_RESPONSE"
            and (
                allowed_source_types is None
                or "OperationalException" in allowed_source_types
            )
        ):
            pending = db.session.scalar(
                select(OperationalException.id).where(
                    OperationalException.organization_id == shipment.organization_id,
                    OperationalException.operational_shipment_id == shipment.id,
                    OperationalException.occurred_at >= rule.effective_from,
                ).limit(1)
            ) is not None
        elif (
            rule.process_type == "ACTION_FOLLOW_UP"
            and (
                allowed_source_types is None
                or "OperationalWorkItem" in allowed_source_types
            )
        ):
            pending = db.session.scalar(
                select(OperationalWorkItem.id).where(
                    OperationalWorkItem.organization_id == shipment.organization_id,
                    OperationalWorkItem.operational_shipment_id == shipment.id,
                    OperationalWorkItem.work_type == "FOLLOW_UP",
                    OperationalWorkItem.created_at >= rule.effective_from,
                ).limit(1)
            ) is not None
        if pending:
            break
    return {
        "status": "PENDING_EVALUATION" if pending else "NO_ACTIVE_COMMITMENT" if configured_rules else "NOT_CONFIGURED",
        "status_label": "در انتظار ارزیابی SLA" if pending else "فرایند مشمول فعالی وجود ندارد" if configured_rules else "SLA تعریف نشده",
        "commitments": [],
    }
