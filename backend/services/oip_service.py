"""Deterministic OIP-2 policies, reconciliation, lifecycle and read projections."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib, json
import time
from uuid import uuid4
from sqlalchemy import delete, func, select, text

from backend.extensions import db
from backend.oip_models import OipAttentionProjection, OipFactReference, OipProjectionHealthHistory, OipProjectionState, OipSignal, OipSituation, OipSituationEvidence, OipSituationHistory, OipThresholdPolicy
from backend.operational_models import ExecutionUnit, Milestone, OperationalAudit, OperationalDelay, OperationalException, OperationalShipment, OperationalWorkItem, Project, utcnow
from backend.services.operational_service import OperationalError, organization_for_user, require_permission

PROJECTION_VERSION = "oip-attention-v1"
HEALTH_POLICY_VERSION = "oip-health-watermark-v1"
HEALTH_STATES = {"FRESH", "STALE", "REBUILDING", "DEGRADED"}
POLICIES = {
 "NEXT_MILESTONE_OVERDUE": {"id":"SIG-OIP-001","version":"1.1.0","configured":"GOVERNED","gap":"an active authoritative overdue-tolerance policy and due time are required","recommendation":"Investigate the overdue milestone through the shipment timeline."},
 "CHECKPOINT_OVERDUE": {"id":"SIG-OIP-002","version":"1.0.0","configured":True,"recommendation":"Review the overdue checkpoint and current route timeline."},
 "ROUTE_DEPENDENCY_BLOCKED": {"id":"SIG-OIP-003","version":"1.0.0","configured":True,"recommendation":"Resolve the explicit predecessor dependency through route operations."},
 "REPLAN_REQUIRED": {"id":"SIG-OIP-004-LOCAL-24H","version":"1.0.0-local","configured":True,"recommendation":"Review the active plan and use the existing replan command if authorized."},
 "DOCUMENT_READINESS_BLOCKED": {"id":"SIG-OIP-005","version":"1.0.0","configured":True,"recommendation":"Review the missing or insufficient document assessment in MDPM."},
 "ACTIVE_DELAY_OR_EXCEPTION": {"id":"SIG-OIP-006","version":"1.0.0","configured":True,"recommendation":"Review the active delay or exception using its existing operational command."},
 "EXECUTION_UNIT_STALE": {"id":"SIG-OIP-007","version":"1.1.0","configured":"GOVERNED","gap":"an active authoritative stale threshold is required","recommendation":"Review the execution-unit event timeline."},
}
RANK = {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}

def _hash(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def policy_catalog(): return [{"situation_type":k,**v} for k,v in POLICIES.items()]

def _projection_lock(org):
    if db.session.get_bind().dialect.name == "postgresql":
        db.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(org)})

def _source_watermark(org):
    """Fingerprint authoritative OIP inputs; equality is the governed freshness policy."""
    snapshots=[]
    for model in (OperationalWorkItem, OperationalDelay, OperationalException):
        snapshots.append(db.session.execute(select(func.count(model.id),func.max(model.id),func.max(model.version)).where(model.organization_id==org)).one())
    snapshots.append(db.session.execute(select(func.count(ExecutionUnit.id),func.max(ExecutionUnit.id),func.max(ExecutionUnit.version)).join(Project,ExecutionUnit.project_id==Project.id).where(Project.organization_id==org)).one())
    return "src:" + _hash([[v for v in row] for row in snapshots])[:48]

def _health_history(state, old, new, code, reason=None):
    db.session.add(OipProjectionHealthHistory(
        organization_id=state.organization_id,from_state=old,to_state=new,
        reason_code=code,reason=reason,projection_version=state.projection_version,
        policy_version=state.policy_version,run_id=state.active_run_id,
        source_watermark=state.source_watermark,processed_watermark=state.processed_watermark,
        occurred_at=state.calculated_at,
    ))

def _set_health(state, new, *, code, now, reason=None):
    if new not in HEALTH_STATES: raise ValueError("unsupported OIP projection health state")
    old=state.status
    state.status=new;state.calculated_at=now;state.version=(state.version or 0)+1
    if old != new or code.endswith("FAILED"):
        _health_history(state,old,new,code,reason)

def _safe_failure(exc):
    if isinstance(exc, OperationalError): return "RECONCILIATION_FAILED", "Projection reconciliation failed."
    return "PROJECTION_OPERATION_FAILED", "Projection operation failed."

def _state(org, *, lock=False, create=False, now=None):
    q=select(OipProjectionState).where(OipProjectionState.organization_id==org)
    if lock:q=q.with_for_update()
    state=db.session.scalar(q)
    if not state and create:
        at=now or utcnow(); watermark=_source_watermark(org)
        state=OipProjectionState(organization_id=org,status="STALE",source_watermark=watermark,
            processed_watermark=None,projection_version=PROJECTION_VERSION,policy_version=HEALTH_POLICY_VERSION,
            calculated_at=at,version=1)
        db.session.add(state);db.session.flush();_health_history(state,None,"STALE","PROJECTION_NOT_YET_RECONCILED")
    return state

def projection_health(user, *, refresh=True):
    require_permission(user,"oip.read");org=organization_for_user(user["id"]);now=utcnow()
    _projection_lock(org);state=_state(org,lock=True,create=True,now=now)
    if refresh and state.status in ("FRESH","STALE"):
        current=_source_watermark(org);state.source_watermark=current
        target="FRESH" if state.processed_watermark == current else "STALE"
        _set_health(state,target,code="WATERMARKS_MATCH" if target=="FRESH" else "SOURCE_AHEAD_OF_PROJECTION",now=now)
        db.session.commit()
    return _serialize_health(state)

def _serialize_health(state):
    return {"health_state":state.status,"calculated_at":state.calculated_at.isoformat(),
        "source_watermark":state.source_watermark,"processed_watermark":state.processed_watermark,
        "projection_version":state.projection_version,"policy_version":state.policy_version,
        "reason_code":state.failure_code if state.status=="DEGRADED" else ("SOURCE_AHEAD_OF_PROJECTION" if state.status=="STALE" else ("REBUILD_IN_PROGRESS" if state.status=="REBUILDING" else None)),
        "reason":state.last_error if state.status=="DEGRADED" else None,
        "last_success_at":state.last_success_at.isoformat() if state.last_success_at else None,
        "rebuild_started_at":state.rebuild_started_at.isoformat() if state.rebuild_started_at else None,
        "rebuild_completed_at":state.rebuild_completed_at.isoformat() if state.rebuild_completed_at else None,
        "last_failure_at":state.last_failure_at.isoformat() if state.last_failure_at else None,
        "run_id":state.active_run_id,"version":state.version}

_UNIT_SECONDS = {"MINUTE": 60, "HOUR": 3600, "DAY": 86400}

def resolve_threshold(*, organization_id, signal_type, project_public_id=None, service_mode_public_ids=(), at=None):
    """Resolve the first explicitly governed duration by approved scope precedence."""
    at = at or utcnow()
    candidates = db.session.scalars(select(OipThresholdPolicy).where(
        OipThresholdPolicy.organization_id == organization_id,
        OipThresholdPolicy.signal_type == signal_type,
        OipThresholdPolicy.is_active.is_(True),
        OipThresholdPolicy.effective_from <= at,
        (OipThresholdPolicy.effective_to.is_(None) | (OipThresholdPolicy.effective_to > at)),
    )).all()
    scopes = []
    if project_public_id:
        scopes.append(("PROJECT", (project_public_id,)))
    if service_mode_public_ids:
        scopes.append(("SERVICE_MODE", tuple(service_mode_public_ids)))
    scopes.append(("ENTERPRISE", ("ENTERPRISE",)))
    for scope_type, public_ids in scopes:
        eligible = [p for p in candidates if p.scope_type == scope_type and p.scope_public_id in public_ids]
        if eligible:
            policy = max(eligible, key=lambda p: (p.version, p.effective_from, p.id))
            seconds = policy.value * _UNIT_SECONDS[policy.unit]
            return {"status":"CONFIGURED","duration":timedelta(seconds=seconds),"value":policy.value,"unit":policy.unit,"scope":policy.scope_type,"scope_public_id":policy.scope_public_id,"policy_public_id":policy.public_id,"policy_version":policy.version,"authority":policy.authority,"source":policy.source}
    return {"status":"INACTIVE_UNCONFIGURED","reason":"NO_ACTIVE_EFFECTIVE_AUTHORITATIVE_THRESHOLD","signal_type":signal_type}

def evaluate_next_milestone_overdue(*, organization_id, project_public_id, subject_public_id, dimensions, source_public_id, source_version, due_at, occurred_at, lifecycle_status, calculated_at=None, due_source="RUNTIME_OPERATIONAL_DUE"):
    now = calculated_at or utcnow()
    threshold = resolve_threshold(organization_id=organization_id, signal_type="NEXT_MILESTONE_OVERDUE", project_public_id=project_public_id, at=now)
    if due_at is None:
        return {"status":"INACTIVE_UNCONFIGURED","reason":"NO_AUTHORITATIVE_DUE_TIME","threshold":threshold}
    if threshold["status"] != "CONFIGURED":
        return threshold
    eligible = lifecycle_status not in {"COMPLETED","SKIPPED","CANCELLED"}
    active = eligible and now > due_at + threshold["duration"]
    explanation = {k:v for k,v in threshold.items() if k != "duration"}
    explanation.update({"time_source":due_source,"effective_due_at":due_at.isoformat(),"evaluated_at":now.isoformat(),"reason":"AFTER_AUTHORIZED_TOLERANCE" if active else ("MILESTONE_NOT_ELIGIBLE" if not eligible else "NOT_AFTER_AUTHORIZED_TOLERANCE")})
    return observe(organization_id=organization_id,situation_type="NEXT_MILESTONE_OVERDUE",subject_type="SHIPMENT",subject_public_id=subject_public_id,dimensions=dimensions,source_domain="OPERATIONAL_EXECUTION",source_type="OperationalMilestoneDue",source_public_id=source_public_id,source_version=source_version,occurred_at=occurred_at,due_at=due_at,severity="HIGH",urgency="HIGH",active=active,calculated_at=now,evidence={"kind":"operational_milestone_due","explanation":explanation},policy_evaluation=explanation)

def evaluate_execution_unit_stale(*, organization_id, project_public_id, unit, calculated_at=None):
    now = calculated_at or utcnow()
    threshold = resolve_threshold(organization_id=organization_id, signal_type="EXECUTION_UNIT_STALE", project_public_id=project_public_id, at=now)
    if threshold["status"] != "CONFIGURED":
        return threshold
    eligible = unit.is_active and unit.lifecycle_status in {"ready","in_progress","arrived"}
    active = eligible and (unit.last_event_at is None or unit.last_event_at.replace(tzinfo=unit.last_event_at.tzinfo or timezone.utc) < now - threshold["duration"])
    explanation = {k:v for k,v in threshold.items() if k != "duration"}
    explanation.update({"time_source":"LATEST_OPERATIONAL_EVENT_OCCURRED_AT","latest_activity_at":unit.last_event_at.isoformat() if unit.last_event_at else None,"eligible_lifecycle_states":["ready","in_progress","arrived"],"evaluated_at":now.isoformat(),"reason":"PAST_AUTHORIZED_FRESHNESS_THRESHOLD" if active else ("LIFECYCLE_NOT_ELIGIBLE" if not eligible else "RECENT_OPERATIONAL_ACTIVITY")})
    return observe(organization_id=organization_id,situation_type="EXECUTION_UNIT_STALE",subject_type="EXECUTION_UNIT",subject_public_id=unit.public_id,dimensions={"project_public_id":project_public_id},source_domain="EXECUTION_ENGINE",source_type="ExecutionUnitActivity",source_public_id=unit.public_id,source_version=unit.version,occurred_at=unit.last_event_at or unit.created_at,recorded_at=unit.updated_at,severity="MEDIUM",urgency="MEDIUM",active=active,calculated_at=now,evidence={"kind":"execution_unit_activity","explanation":explanation},policy_evaluation=explanation)

def _history(s, event, old, new, actor=None, reason=None, metadata=None):
    db.session.add(OipSituationHistory(public_id=str(uuid4()),organization_id=s.organization_id,situation_id=s.id,event_type=event,from_status=old,to_status=new,actor_user_id=actor,reason=reason,metadata_json=metadata or {},occurred_at=utcnow()))

def _lock_identity(identity):
    """Serialize one logical Situation for the transaction on real PostgreSQL."""
    if db.session.get_bind().dialect.name == "postgresql":
        db.session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"), {"identity": identity})

def _utc_aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def observe(*, organization_id, situation_type, subject_type, subject_public_id, dimensions, source_domain, source_type, source_public_id, source_version, occurred_at, recorded_at=None, correlation_id=None, due_at=None, severity="MEDIUM", urgency="MEDIUM", active=True, source_watermark=None, evidence=None, work_item_id=None, calculated_at=None, policy_evaluation=None):
    """Apply one trusted adapter observation. Callers must tenant-resolve the source first."""
    policy=POLICIES.get(situation_type)
    if not policy: raise OperationalError("UNSUPPORTED_SITUATION_TYPE","Only the approved seven OIP situation types are allowed.")
    if policy["configured"] == "GOVERNED" and not policy_evaluation: return {"status":"INACTIVE_UNCONFIGURED","reason":"GOVERNED_EVALUATION_REQUIRED","policy":policy,"situation_type":situation_type}
    now=calculated_at or utcnow(); watermark=source_watermark or f"{source_type}:{source_public_id}:{source_version}"
    identity=_hash([organization_id,situation_type,subject_public_id,dimensions,policy["id"],policy["version"].split(".")[0]])
    _lock_identity(identity)
    fact=db.session.scalar(select(OipFactReference).where(OipFactReference.organization_id==organization_id,OipFactReference.source_domain==source_domain,OipFactReference.source_type==source_type,OipFactReference.source_public_id==source_public_id,OipFactReference.source_version==str(source_version)))
    if not fact:
        fact=OipFactReference(public_id=str(uuid4()),organization_id=organization_id,source_domain=source_domain,source_type=source_type,source_public_id=source_public_id,subject_type=subject_type,subject_public_id=subject_public_id,occurred_at=occurred_at,recorded_at=recorded_at,source_version=str(source_version),correlation_id=correlation_id,evidence_reference=evidence or {"kind":source_type,"public_id":source_public_id},validity="CURRENT",resolved_at=now);db.session.add(fact);db.session.flush()
    signal=db.session.scalar(select(OipSignal).where(OipSignal.organization_id==organization_id,OipSignal.dedup_key==identity,OipSignal.source_watermark==watermark))
    if not signal:
        signal=OipSignal(public_id=str(uuid4()),organization_id=organization_id,signal_type=situation_type,policy_id=policy["id"],policy_version=str(policy_evaluation.get("policy_version")) if policy_evaluation else policy["version"],subject_type=subject_type,subject_public_id=subject_public_id,dedup_key=identity,active=active,derivation={"condition":"authoritative source predicate","inputs":dimensions,"evaluation":policy_evaluation},observed_at=now,source_watermark=watermark);db.session.add(signal);db.session.flush()
    s=db.session.scalar(select(OipSituation).where(OipSituation.organization_id==organization_id,OipSituation.identity_key==identity).with_for_update())
    if s and _utc_aware(now) < _utc_aware(s.calculated_at):
        return {"status":"STALE_OBSERVATION","public_id":s.public_id,"current_watermark":s.source_watermark}
    if not active:
        if s and s.status not in ("RESOLVED","EXPIRED"):
            old=s.status;s.status="RESOLVED";s.resolved_at=now;s.disposition_reason="AUTHORITATIVE_CONDITION_CLEARED";s.last_changed_at=now;s.version+=1;_history(s,"AUTO_RESOLVED",old,s.status,reason=s.disposition_reason)
        return {"status":"CLEARED","public_id":s.public_id if s else None}
    priority="CRITICAL" if severity=="CRITICAL" or urgency=="CRITICAL" else "HIGH" if severity=="HIGH" or urgency=="HIGH" else "MEDIUM" if severity=="MEDIUM" or urgency=="MEDIUM" else "LOW"
    explanation={"policy":"lexicographic-v1","drivers":[{"name":"urgency","value":urgency},{"name":"severity","value":severity},{"name":"due_at","value":due_at.isoformat() if due_at else None}],"tie_breaker":"public_id"}
    if not s:
        s=OipSituation(public_id=str(uuid4()),organization_id=organization_id,identity_key=identity,situation_type=situation_type,subject_type=subject_type,subject_public_id=subject_public_id,identity_dimensions=dimensions,status="OPEN",severity=severity,urgency=urgency,priority=priority,priority_explanation={**explanation,"evaluation":policy_evaluation},first_detected_at=now,last_detected_at=now,last_changed_at=now,due_at=due_at,occurrence_count=1,policy_id=policy["id"],policy_version=str(policy_evaluation.get("policy_version")) if policy_evaluation else policy["version"],projection_version=PROJECTION_VERSION,calculated_at=now,source_watermark=watermark,freshness_status="FRESH",version=1);db.session.add(s);db.session.flush();_history(s,"DETECTED",None,"OPEN")
    else:
        if s.status == "SNOOZED" and s.snoozed_until and _utc_aware(s.snoozed_until) <= _utc_aware(now):
            old=s.status;s.status="OPEN";s.last_changed_at=now;s.version+=1
            _history(s,"RETURNED_TO_ATTENTION",old,"OPEN",reason="SNOOZE_EXPIRED",metadata={"snoozed_until":s.snoozed_until.isoformat()})
        if s.status in ("RESOLVED","DISMISSED","EXPIRED") and watermark != s.source_watermark:
            old=s.status;s.status="OPEN";s.occurrence_count+=1;s.resolved_at=None;s.disposition_reason=None;_history(s,"REOPENED",old,"OPEN")
        elif s.status in ("RESOLVED","DISMISSED","EXPIRED"):
            return {"status":"TERMINAL_PRESERVED","public_id":s.public_id}
        changed=(s.severity,s.urgency,s.priority,s.due_at)!=(severity,urgency,priority,due_at)
        s.severity=severity;s.urgency=urgency;s.priority=priority;s.priority_explanation={**explanation,"evaluation":policy_evaluation};s.due_at=due_at;s.last_detected_at=now;s.calculated_at=now;s.source_watermark=watermark;s.freshness_status="FRESH";s.policy_version=str(policy_evaluation.get("policy_version")) if policy_evaluation else policy["version"]
        if changed:s.last_changed_at=now;s.version+=1
    link=db.session.get(OipSituationEvidence,(s.id,fact.id,signal.id))
    if not link: db.session.add(OipSituationEvidence(situation_id=s.id,fact_reference_id=fact.id,signal_id=signal.id,is_current=True,linked_at=now))
    projection=db.session.get(OipAttentionProjection,s.id)
    if not projection: db.session.add(OipAttentionProjection(situation_id=s.id,operational_work_item_id=work_item_id,calculated_at=now,source_watermark=watermark,projection_version=PROJECTION_VERSION))
    else: projection.operational_work_item_id=work_item_id or projection.operational_work_item_id;projection.calculated_at=now;projection.source_watermark=watermark
    return {"status":"ACTIVE","public_id":s.public_id}

def rebuild_attention_projections(user, calculation_time=None, _failure_point=None, _test_pause_seconds=0):
    """Recreate only disposable attention rows; durable Situation state is untouched."""
    require_permission(user,"oip.reconcile");org=organization_for_user(user["id"]);now=calculation_time or utcnow();run_id=str(uuid4())
    _projection_lock(org);state=_state(org,lock=True,create=True,now=now)
    if state.status == "REBUILDING":
        db.session.rollback();raise OperationalError("PROJECTION_OPERATION_IN_PROGRESS","A projection operation is already active.",409)
    state.active_run_id=run_id;state.rebuild_started_at=now;state.source_watermark=_source_watermark(org);state.failure_code=None;state.last_error=None
    _set_health(state,"REBUILDING",code="REBUILD_STARTED",now=now);db.session.commit()
    if _test_pause_seconds:
        time.sleep(_test_pause_seconds)
    try:
        _projection_lock(org);state=_state(org,lock=True);source=_source_watermark(org)
        if state.active_run_id != run_id: raise OperationalError("REBUILD_SUPERSEDED","Projection rebuild was superseded.",409)
        db.session.execute(delete(OipAttentionProjection).where(OipAttentionProjection.situation_id.in_(select(OipSituation.id).where(OipSituation.organization_id==org))))
        db.session.flush()
        if _failure_point == "after_delete": raise RuntimeError("controlled projection rebuild failure")
        for situation in db.session.scalars(select(OipSituation).where(OipSituation.organization_id==org).with_for_update()):
            db.session.add(OipAttentionProjection(situation_id=situation.id,calculated_at=now,source_watermark=situation.source_watermark,projection_version=PROJECTION_VERSION))
        state.source_watermark=source;state.processed_watermark=source;state.last_success_at=now;state.rebuild_completed_at=now;state.failure_code=None;state.last_error=None
        _set_health(state,"FRESH",code="REBUILD_SUCCEEDED",now=now);db.session.commit()
        return {"status":state.status,**_serialize_health(state)}
    except Exception as exc:
        db.session.rollback();_projection_lock(org);state=_state(org,lock=True,create=True,now=now);code,reason=_safe_failure(exc)
        state.active_run_id=run_id;state.last_failure_at=utcnow();state.failure_code="REBUILD_FAILED";state.last_error="Projection rebuild failed."
        _set_health(state,"DEGRADED",code="REBUILD_FAILED",now=state.last_failure_at,reason=state.last_error);db.session.commit()
        raise OperationalError("REBUILD_FAILED",reason,503) from exc

def reconcile(user, calculation_time=None, _failure_point=None):
    require_permission(user,"oip.reconcile");org=organization_for_user(user["id"]);now=calculation_time or utcnow();run_id=str(uuid4())
    _projection_lock(org);state=_state(org,lock=True,create=True,now=now)
    if state.status == "REBUILDING":
        db.session.rollback();raise OperationalError("PROJECTION_OPERATION_IN_PROGRESS","A projection operation is already active.",409)
    # Reconciliation is a governed recovery operation and truthfully exposes REBUILDING.
    state.active_run_id=run_id;state.rebuild_started_at=now;state.source_watermark=_source_watermark(org);state.failure_code=None;state.last_error=None
    _set_health(state,"REBUILDING",code="RECONCILIATION_STARTED",now=now);db.session.commit();seen=[]
    try:
        _projection_lock(org);state=_state(org,lock=True)
        if state.active_run_id != run_id: raise OperationalError("RECONCILIATION_SUPERSEDED","Projection reconciliation was superseded.",409)
        mapping={"OVERDUE_MILESTONE":"NEXT_MILESTONE_OVERDUE","CHECKPOINT_OVERDUE":"CHECKPOINT_OVERDUE","ROUTE_DEPENDENCY_BLOCKED":"ROUTE_DEPENDENCY_BLOCKED","REPLAN_REQUIRED":"REPLAN_REQUIRED"}
        for item in db.session.scalars(select(OperationalWorkItem).where(OperationalWorkItem.organization_id==org,OperationalWorkItem.status=="open")):
            shipment=db.session.get(OperationalShipment,item.operational_shipment_id);typ=mapping[item.work_type]
            dimensions={"work_type":item.work_type,"milestone_id":item.milestone_id,"checkpoint_id":item.checkpoint_id,"route_plan_id":item.route_plan_id}
            if typ == "NEXT_MILESTONE_OVERDUE":
                project=db.session.get(Project,shipment.project_id);milestone=db.session.get(Milestone,item.milestone_id)
                result=evaluate_next_milestone_overdue(organization_id=org,project_public_id=project.public_id,subject_public_id=shipment.public_id,dimensions=dimensions,source_public_id=milestone.public_id,source_version=milestone.version,due_at=item.due_at,occurred_at=item.detected_at,lifecycle_status=milestone.lifecycle_status,calculated_at=now,due_source="RUNTIME_OPERATIONAL_WORK_ITEM_DUE")
            else:
                result=observe(organization_id=org,situation_type=typ,subject_type="SHIPMENT",subject_public_id=shipment.public_id,dimensions=dimensions,source_domain="OPERATIONAL_EXECUTION",source_type="OperationalWorkItem",source_public_id=f"owi-{item.id}",source_version=item.version,occurred_at=item.detected_at,due_at=item.due_at,severity=item.severity.upper() if item.severity.upper() in RANK else "MEDIUM",urgency="HIGH" if item.due_at<=now else "MEDIUM",work_item_id=item.id,calculated_at=now,evidence={"kind":"operational_work_item","shipment_public_id":shipment.public_id})
            seen.append(result)
        if _failure_point == "after_work_items": raise RuntimeError("controlled reconciliation failure")
        for model,source_type,time_field in ((OperationalDelay,"OperationalDelay","started_at"),(OperationalException,"OperationalException","occurred_at")):
            for row in db.session.scalars(select(model).where(model.organization_id==org,model.resolved_at.is_(None))):
                shipment=db.session.get(OperationalShipment,row.operational_shipment_id)
                seen.append(observe(organization_id=org,situation_type="ACTIVE_DELAY_OR_EXCEPTION",subject_type="SHIPMENT",subject_public_id=shipment.public_id,dimensions={"source_type":source_type,"source_public_id":row.public_id},source_domain="OPERATIONAL_EXECUTION",source_type=source_type,source_public_id=row.public_id,source_version=row.version,occurred_at=getattr(row,time_field),severity="HIGH",urgency="HIGH",calculated_at=now,evidence={"kind":source_type,"public_id":row.public_id}))
        for unit,project in db.session.execute(select(ExecutionUnit,Project).join(Project,ExecutionUnit.project_id==Project.id).where(Project.organization_id==org)):
            seen.append(evaluate_execution_unit_stale(organization_id=org,project_public_id=project.public_id,unit=unit,calculated_at=now))
        source=_source_watermark(org);state.source_watermark=source;state.processed_watermark=source;state.last_success_at=now;state.rebuild_completed_at=now;state.failure_code=None;state.last_error=None
        _set_health(state,"FRESH",code="RECONCILIATION_SUCCEEDED",now=now);db.session.commit()
        return {"status":state.status,"calculated_at":now.isoformat(),"projection_health":_serialize_health(state),"results":seen,"policy_gaps":[p for p in policy_catalog() if not p["configured"]]}
    except Exception as exc:
        db.session.rollback();_projection_lock(org);state=_state(org,lock=True,create=True,now=now);code,reason=_safe_failure(exc)
        state.active_run_id=run_id;state.last_failure_at=utcnow();state.failure_code=code;state.last_error=reason
        _set_health(state,"DEGRADED",code=code,now=state.last_failure_at,reason=reason);db.session.commit()
        if isinstance(exc,OperationalError): raise
        raise OperationalError(code,reason,503) from exc

def _get(public_id,user,permission="oip.read",lock=False):
    require_permission(user,permission);org=organization_for_user(user["id"]);q=select(OipSituation).where(OipSituation.organization_id==org,OipSituation.public_id==public_id)
    if lock:q=q.with_for_update()
    s=db.session.scalar(q)
    if not s:raise OperationalError("SITUATION_NOT_FOUND","Situation not found.",404)
    return s

def serialize(s):
    return {"public_id":s.public_id,"type":s.situation_type,"subject":{"type":s.subject_type,"public_id":s.subject_public_id},"status":s.status,"severity":s.severity,"urgency":s.urgency,"priority":s.priority,"priority_explanation":s.priority_explanation,"owner":{"state":"ASSIGNED" if s.assignee_user_id else "UNASSIGNED","assignee_public_id":None},"first_detected_at":s.first_detected_at.isoformat(),"last_changed_at":s.last_changed_at.isoformat(),"due_at":s.due_at.isoformat() if s.due_at else None,"snoozed_until":s.snoozed_until.isoformat() if s.snoozed_until else None,"occurrence_count":s.occurrence_count,"policy":{"id":s.policy_id,"version":s.policy_version},"freshness":{"status":s.freshness_status,"calculated_at":s.calculated_at.isoformat(),"source_watermark":s.source_watermark,"projection_version":s.projection_version,"reason":s.freshness_reason},"version":s.version}

def queue(user):
    require_permission(user,"oip.read");org=organization_for_user(user["id"]);now=utcnow();rows=db.session.scalars(select(OipSituation).where(OipSituation.organization_id==org,OipSituation.status.in_(("OPEN","ACKNOWLEDGED","IN_PROGRESS","SNOOZED")))).all();rows=[s for s in rows if s.status!="SNOOZED" or (s.snoozed_until and s.snoozed_until<=now)];rows.sort(key=lambda s:(RANK[s.priority],RANK[s.urgency],RANK[s.severity],s.due_at or datetime.max.replace(tzinfo=timezone.utc),s.public_id));return [serialize(s) for s in rows]

def transition(public_id,action,payload,user):
    s=_get(public_id,user,"oip.manage",True);expected=payload.get("expected_version")
    if expected!=s.version:raise OperationalError("VERSION_CONFLICT","Situation version is stale.",409)
    old=s.status;reason=(payload.get("reason") or "").strip();now=utcnow()
    targets={"acknowledge":"ACKNOWLEDGED","start":"IN_PROGRESS","snooze":"SNOOZED","resolve":"RESOLVED","dismiss":"DISMISSED"}
    if action in ("snooze","dismiss","resolve") and not reason:raise OperationalError("REASON_REQUIRED","A reason is required.")
    if action=="snooze":
        try: until=datetime.fromisoformat(payload.get("until","").replace("Z","+00:00"))
        except ValueError: raise OperationalError("SNOOZE_UNTIL_REQUIRED","Snooze requires a valid until timestamp.")
        if until<=now:raise OperationalError("INVALID_SNOOZE_UNTIL","Snooze expiry must be in the future.")
        s.snoozed_until=until
    if action=="claim":
        s.assignee_user_id=int(user["id"]);new=old
    elif action in ("assign","reassign"):
        raise OperationalError("ACTION_GAP","Assign/reassign requires an opaque operational member identity contract.",501)
    elif action in targets:new=targets[action];s.status=new
    else:raise OperationalError("INVALID_TRANSITION","Unsupported Situation transition.")
    if action=="acknowledge":s.acknowledged_at=now
    if action=="start":s.intervention_started_at=now
    if action in ("resolve","dismiss"):s.resolved_at=now;s.disposition_reason=reason
    s.last_changed_at=now;s.version+=1;_history(s,action.upper(),old,new,int(user["id"]),reason,{"until":payload.get("until")})
    db.session.add(OperationalAudit(organization_id=s.organization_id,actor_user_id=int(user["id"]),action=f"OIP_{action.upper()}",entity_type="OipSituation",entity_id=s.id,metadata_json={"public_id":s.public_id,"expected_version":expected,"reason":reason}));db.session.commit();return serialize(s)

def detail(public_id,user):
    health=projection_health(user);s=_get(public_id,user);base=serialize(s);links=db.session.execute(select(OipSituationEvidence,OipFactReference,OipSignal).join(OipFactReference,OipSituationEvidence.fact_reference_id==OipFactReference.id).join(OipSignal,OipSituationEvidence.signal_id==OipSignal.id).where(OipSituationEvidence.situation_id==s.id)).all();history=db.session.scalars(select(OipSituationHistory).where(OipSituationHistory.situation_id==s.id).order_by(OipSituationHistory.occurred_at)).all();policy=POLICIES[s.situation_type]
    evaluation=s.priority_explanation.get("evaluation") or {}
    missing=[] if evaluation.get("status")=="CONFIGURED" else ([policy["gap"]] if policy.get("gap") else [])
    base.update({"projection_health":health,"evidence":[{"fact_public_id":f.public_id,"source_domain":f.source_domain,"source_type":f.source_type,"source_public_id":f.source_public_id,"source_version":f.source_version,"validity":f.validity,"reference":f.evidence_reference,"signal_public_id":sig.public_id} for _,f,sig in links],"timeline":[{"event":h.event_type,"from":h.from_status,"to":h.to_status,"reason":h.reason,"at":h.occurred_at.isoformat()} for h in history],"decision_context":{"read_only":True,"time_pressure":s.urgency,"active_blockers":[s.situation_type],"missing_information":missing,"projection_health":health,"permissions":{"can_manage":True},"versions":{"situation":s.version,"policy":s.policy_version,"projection":s.projection_version,"projection_health_policy":health["policy_version"]}},"recommendation":{"advisory":True,"basis":s.priority_explanation,"suggested_action":policy["recommendation"],"allowed_command_reference":_action(s),"automatic_execution":False}});return base

def _action(s):
    if s.situation_type=="EXECUTION_UNIT_STALE":
        project=s.identity_dimensions.get("project_public_id")
        return {"method":"GET","path":f"/api/v2/projects/{project}/execution-units/{s.subject_public_id}/timeline"}
    if s.situation_type=="DOCUMENT_READINESS_BLOCKED":return {"method":"GET","path":f"/api/operational-shipments/{s.subject_public_id}/document-readiness/next"}
    if s.situation_type in ("CHECKPOINT_OVERDUE","ROUTE_DEPENDENCY_BLOCKED","REPLAN_REQUIRED"):return {"method":"GET","path":f"/api/operational-shipments/{s.subject_public_id}/timeline"}
    return {"method":"GET","path":f"/api/operational-shipments/{s.subject_public_id}"}
