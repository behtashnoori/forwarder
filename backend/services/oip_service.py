"""Deterministic OIP-2 policies, reconciliation, lifecycle and read projections."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json
from uuid import uuid4
from sqlalchemy import select

from backend.extensions import db
from backend.oip_models import OipAttentionProjection, OipFactReference, OipProjectionState, OipSignal, OipSituation, OipSituationEvidence, OipSituationHistory
from backend.operational_models import OperationalAudit, OperationalDelay, OperationalException, OperationalShipment, OperationalWorkItem, utcnow
from backend.services.operational_service import OperationalError, organization_for_user, require_permission

PROJECTION_VERSION = "oip-attention-v1"
POLICIES = {
 "NEXT_MILESTONE_OVERDUE": {"id":"SIG-OIP-001","version":"1.0.0","configured":False,"gap":"overdue tolerance and effective-time precedence require authority","recommendation":"Investigate the overdue milestone through the shipment timeline."},
 "CHECKPOINT_OVERDUE": {"id":"SIG-OIP-002","version":"1.0.0","configured":True,"recommendation":"Review the overdue checkpoint and current route timeline."},
 "ROUTE_DEPENDENCY_BLOCKED": {"id":"SIG-OIP-003","version":"1.0.0","configured":True,"recommendation":"Resolve the explicit predecessor dependency through route operations."},
 "REPLAN_REQUIRED": {"id":"SIG-OIP-004-LOCAL-24H","version":"1.0.0-local","configured":True,"recommendation":"Review the active plan and use the existing replan command if authorized."},
 "DOCUMENT_READINESS_BLOCKED": {"id":"SIG-OIP-005","version":"1.0.0","configured":True,"recommendation":"Review the missing or insufficient document assessment in MDPM."},
 "ACTIVE_DELAY_OR_EXCEPTION": {"id":"SIG-OIP-006","version":"1.0.0","configured":True,"recommendation":"Review the active delay or exception using its existing operational command."},
 "EXECUTION_UNIT_STALE": {"id":"SIG-OIP-007","version":"1.0.0","configured":False,"gap":"no authoritative execution-unit freshness threshold","recommendation":"Review the execution-unit event timeline."},
}
RANK = {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}

def _hash(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def policy_catalog(): return [{"situation_type":k,**v} for k,v in POLICIES.items()]

def _history(s, event, old, new, actor=None, reason=None, metadata=None):
    db.session.add(OipSituationHistory(public_id=str(uuid4()),organization_id=s.organization_id,situation_id=s.id,event_type=event,from_status=old,to_status=new,actor_user_id=actor,reason=reason,metadata_json=metadata or {},occurred_at=utcnow()))

def observe(*, organization_id, situation_type, subject_type, subject_public_id, dimensions, source_domain, source_type, source_public_id, source_version, occurred_at, recorded_at=None, correlation_id=None, due_at=None, severity="MEDIUM", urgency="MEDIUM", active=True, source_watermark=None, evidence=None, work_item_id=None, calculated_at=None):
    """Apply one trusted adapter observation. Callers must tenant-resolve the source first."""
    policy=POLICIES.get(situation_type)
    if not policy: raise OperationalError("UNSUPPORTED_SITUATION_TYPE","Only the approved seven OIP situation types are allowed.")
    if not policy["configured"]: return {"status":"INACTIVE_UNCONFIGURED","policy":policy,"situation_type":situation_type}
    now=calculated_at or utcnow(); watermark=source_watermark or f"{source_type}:{source_public_id}:{source_version}"
    identity=_hash([organization_id,situation_type,subject_public_id,dimensions,policy["id"],policy["version"].split(".")[0]])
    fact=db.session.scalar(select(OipFactReference).where(OipFactReference.organization_id==organization_id,OipFactReference.source_domain==source_domain,OipFactReference.source_type==source_type,OipFactReference.source_public_id==source_public_id,OipFactReference.source_version==str(source_version)))
    if not fact:
        fact=OipFactReference(public_id=str(uuid4()),organization_id=organization_id,source_domain=source_domain,source_type=source_type,source_public_id=source_public_id,subject_type=subject_type,subject_public_id=subject_public_id,occurred_at=occurred_at,recorded_at=recorded_at,source_version=str(source_version),correlation_id=correlation_id,evidence_reference=evidence or {"kind":source_type,"public_id":source_public_id},validity="CURRENT",resolved_at=now);db.session.add(fact);db.session.flush()
    signal=db.session.scalar(select(OipSignal).where(OipSignal.organization_id==organization_id,OipSignal.dedup_key==identity,OipSignal.source_watermark==watermark))
    if not signal:
        signal=OipSignal(public_id=str(uuid4()),organization_id=organization_id,signal_type=situation_type,policy_id=policy["id"],policy_version=policy["version"],subject_type=subject_type,subject_public_id=subject_public_id,dedup_key=identity,active=active,derivation={"condition":"authoritative source predicate","inputs":dimensions,"threshold_gap":policy.get("gap")},observed_at=now,source_watermark=watermark);db.session.add(signal);db.session.flush()
    s=db.session.scalar(select(OipSituation).where(OipSituation.organization_id==organization_id,OipSituation.identity_key==identity))
    if not active:
        if s and s.status not in ("RESOLVED","EXPIRED"):
            old=s.status;s.status="RESOLVED";s.resolved_at=now;s.disposition_reason="AUTHORITATIVE_CONDITION_CLEARED";s.last_changed_at=now;s.version+=1;_history(s,"AUTO_RESOLVED",old,s.status,reason=s.disposition_reason)
        return {"status":"CLEARED","public_id":s.public_id if s else None}
    priority="CRITICAL" if severity=="CRITICAL" or urgency=="CRITICAL" else "HIGH" if severity=="HIGH" or urgency=="HIGH" else "MEDIUM" if severity=="MEDIUM" or urgency=="MEDIUM" else "LOW"
    explanation={"policy":"lexicographic-v1","drivers":[{"name":"urgency","value":urgency},{"name":"severity","value":severity},{"name":"due_at","value":due_at.isoformat() if due_at else None}],"tie_breaker":"public_id"}
    if not s:
        s=OipSituation(public_id=str(uuid4()),organization_id=organization_id,identity_key=identity,situation_type=situation_type,subject_type=subject_type,subject_public_id=subject_public_id,identity_dimensions=dimensions,status="OPEN",severity=severity,urgency=urgency,priority=priority,priority_explanation=explanation,first_detected_at=now,last_detected_at=now,last_changed_at=now,due_at=due_at,occurrence_count=1,policy_id=policy["id"],policy_version=policy["version"],projection_version=PROJECTION_VERSION,calculated_at=now,source_watermark=watermark,freshness_status="FRESH",version=1);db.session.add(s);db.session.flush();_history(s,"DETECTED",None,"OPEN")
    else:
        if s.status in ("RESOLVED","DISMISSED","EXPIRED"):
            old=s.status;s.status="OPEN";s.occurrence_count+=1;s.resolved_at=None;s.disposition_reason=None;_history(s,"REOPENED",old,"OPEN")
        changed=(s.severity,s.urgency,s.priority,s.due_at)!=(severity,urgency,priority,due_at)
        s.severity=severity;s.urgency=urgency;s.priority=priority;s.priority_explanation=explanation;s.due_at=due_at;s.last_detected_at=now;s.calculated_at=now;s.source_watermark=watermark;s.freshness_status="FRESH"
        if changed:s.last_changed_at=now;s.version+=1
    link=db.session.get(OipSituationEvidence,(s.id,fact.id,signal.id))
    if not link: db.session.add(OipSituationEvidence(situation_id=s.id,fact_reference_id=fact.id,signal_id=signal.id,is_current=True,linked_at=now))
    projection=db.session.get(OipAttentionProjection,s.id)
    if not projection: db.session.add(OipAttentionProjection(situation_id=s.id,operational_work_item_id=work_item_id,calculated_at=now,source_watermark=watermark,projection_version=PROJECTION_VERSION))
    else: projection.operational_work_item_id=work_item_id or projection.operational_work_item_id;projection.calculated_at=now;projection.source_watermark=watermark
    return {"status":"ACTIVE","public_id":s.public_id}

def reconcile(user, calculation_time=None):
    require_permission(user,"oip.reconcile");org=organization_for_user(user["id"]);now=calculation_time or utcnow()
    state=db.session.get(OipProjectionState,org)
    if not state: state=OipProjectionState(organization_id=org,status="REBUILDING",source_watermark="starting",projection_version=PROJECTION_VERSION,calculated_at=now);db.session.add(state)
    else: state.status="REBUILDING";state.calculated_at=now
    db.session.flush();seen=[]
    mapping={"OVERDUE_MILESTONE":"NEXT_MILESTONE_OVERDUE","CHECKPOINT_OVERDUE":"CHECKPOINT_OVERDUE","ROUTE_DEPENDENCY_BLOCKED":"ROUTE_DEPENDENCY_BLOCKED","REPLAN_REQUIRED":"REPLAN_REQUIRED"}
    for item in db.session.scalars(select(OperationalWorkItem).where(OperationalWorkItem.organization_id==org,OperationalWorkItem.status=="open")):
        shipment=db.session.get(OperationalShipment,item.operational_shipment_id);typ=mapping[item.work_type]
        result=observe(organization_id=org,situation_type=typ,subject_type="SHIPMENT",subject_public_id=shipment.public_id,dimensions={"work_type":item.work_type,"milestone_id":item.milestone_id,"checkpoint_id":item.checkpoint_id,"route_plan_id":item.route_plan_id},source_domain="OPERATIONAL_EXECUTION",source_type="OperationalWorkItem",source_public_id=f"owi-{item.id}",source_version=item.version,occurred_at=item.detected_at,due_at=item.due_at,severity=item.severity.upper() if item.severity.upper() in RANK else "MEDIUM",urgency="HIGH" if item.due_at<=now else "MEDIUM",work_item_id=item.id,calculated_at=now,evidence={"kind":"operational_work_item","shipment_public_id":shipment.public_id});seen.append(result)
    for model,source_type,time_field in ((OperationalDelay,"OperationalDelay","started_at"),(OperationalException,"OperationalException","occurred_at")):
        for row in db.session.scalars(select(model).where(model.organization_id==org,model.resolved_at.is_(None))):
            shipment=db.session.get(OperationalShipment,row.operational_shipment_id)
            seen.append(observe(organization_id=org,situation_type="ACTIVE_DELAY_OR_EXCEPTION",subject_type="SHIPMENT",subject_public_id=shipment.public_id,dimensions={"source_type":source_type,"source_public_id":row.public_id},source_domain="OPERATIONAL_EXECUTION",source_type=source_type,source_public_id=row.public_id,source_version=row.version,occurred_at=getattr(row,time_field),severity="HIGH",urgency="HIGH",calculated_at=now,evidence={"kind":source_type,"public_id":row.public_id}))
    state.status="FRESH";state.source_watermark=f"oip:{now.isoformat()}";state.calculated_at=now;db.session.commit()
    return {"status":state.status,"calculated_at":now.isoformat(),"results":seen,"policy_gaps":[p for p in policy_catalog() if not p["configured"]]}

def _get(public_id,user,permission="oip.read",lock=False):
    require_permission(user,permission);org=organization_for_user(user["id"]);q=select(OipSituation).where(OipSituation.organization_id==org,OipSituation.public_id==public_id)
    if lock:q=q.with_for_update()
    s=db.session.scalar(q)
    if not s:raise OperationalError("SITUATION_NOT_FOUND","Situation not found.",404)
    return s

def serialize(s):
    return {"public_id":s.public_id,"type":s.situation_type,"subject":{"type":s.subject_type,"public_id":s.subject_public_id},"status":s.status,"severity":s.severity,"urgency":s.urgency,"priority":s.priority,"priority_explanation":s.priority_explanation,"owner":{"state":"ASSIGNED" if s.assignee_user_id else "UNASSIGNED","assignee_public_id":None},"first_detected_at":s.first_detected_at.isoformat(),"last_changed_at":s.last_changed_at.isoformat(),"due_at":s.due_at.isoformat() if s.due_at else None,"occurrence_count":s.occurrence_count,"policy":{"id":s.policy_id,"version":s.policy_version},"freshness":{"status":s.freshness_status,"calculated_at":s.calculated_at.isoformat(),"source_watermark":s.source_watermark,"projection_version":s.projection_version,"reason":s.freshness_reason},"version":s.version}

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
    s=_get(public_id,user);base=serialize(s);links=db.session.execute(select(OipSituationEvidence,OipFactReference,OipSignal).join(OipFactReference,OipSituationEvidence.fact_reference_id==OipFactReference.id).join(OipSignal,OipSituationEvidence.signal_id==OipSignal.id).where(OipSituationEvidence.situation_id==s.id)).all();history=db.session.scalars(select(OipSituationHistory).where(OipSituationHistory.situation_id==s.id).order_by(OipSituationHistory.occurred_at)).all();policy=POLICIES[s.situation_type]
    base.update({"evidence":[{"fact_public_id":f.public_id,"source_domain":f.source_domain,"source_type":f.source_type,"source_public_id":f.source_public_id,"source_version":f.source_version,"validity":f.validity,"reference":f.evidence_reference,"signal_public_id":sig.public_id} for _,f,sig in links],"timeline":[{"event":h.event_type,"from":h.from_status,"to":h.to_status,"reason":h.reason,"at":h.occurred_at.isoformat()} for h in history],"decision_context":{"read_only":True,"time_pressure":s.urgency,"active_blockers":[s.situation_type],"missing_information":([policy["gap"]] if policy.get("gap") else []),"permissions":{"can_manage":True},"versions":{"situation":s.version,"policy":s.policy_version,"projection":s.projection_version}},"recommendation":{"advisory":True,"basis":s.priority_explanation,"suggested_action":policy["recommendation"],"allowed_command_reference":_action(s),"automatic_execution":False}});return base

def _action(s):
    if s.situation_type=="DOCUMENT_READINESS_BLOCKED":return {"method":"GET","path":f"/api/operational-shipments/{s.subject_public_id}/document-readiness/next"}
    if s.situation_type in ("CHECKPOINT_OVERDUE","ROUTE_DEPENDENCY_BLOCKED","REPLAN_REQUIRED"):return {"method":"GET","path":f"/api/operational-shipments/{s.subject_public_id}/timeline"}
    return {"method":"GET","path":f"/api/operational-shipments/{s.subject_public_id}"}
