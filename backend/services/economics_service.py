"""Application boundary for FE-2 Shipment Economics."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import json
from typing import Any

from sqlalchemy import select

from backend.extensions import db
from backend.economics_models import EconomicAudit, EconomicEvidenceAssociation, EconomicFxRate, EconomicLine, EconomicObservation, EconomicObservationFx
from backend.models import CaseDocumentFile, ExpertQuote, ServiceType
from backend.operational_models import OperationalShipment, Project, utcnow
from backend.services.operational_service import OperationalError, organization_for_user, require_permission, _lock_idempotency_scope

STAGES = {"ESTIMATE", "COMMITMENT", "ACTUAL"}
SIDES = {"REVENUE", "COST"}
CURRENCIES = {"IRR", "USD", "EUR", "GBP", "AED", "CNY", "TRY"}


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _time(value: Any, field: str = "effective_at") -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise OperationalError("INVALID_ECONOMIC_TIME", f"{field} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise OperationalError("INVALID_ECONOMIC_TIME", f"{field} must include a timezone.")
    return parsed.astimezone(timezone.utc)


def money(value: Any) -> tuple[Decimal, str]:
    if not isinstance(value, dict) or not isinstance(value.get("amount"), str):
        raise OperationalError("INVALID_MONEY", "Money requires a decimal-string amount and currency.")
    currency = str(value.get("currency") or "").upper()
    if currency not in CURRENCIES:
        raise OperationalError("INVALID_CURRENCY", "A governed ISO-compatible currency is required.")
    try:
        amount = Decimal(value["amount"])
    except InvalidOperation as exc:
        raise OperationalError("INVALID_MONEY", "Money amount is not an exact decimal.") from exc
    if not amount.is_finite() or amount < 0 or -amount.as_tuple().exponent > 6:
        raise OperationalError("INVALID_MONEY", "Money must be non-negative with at most six decimal places.")
    return amount, currency


def money_json(amount: Decimal, currency: str) -> dict[str, str]:
    return {"amount": format(amount, "f"), "currency": currency}


def _shipment(public_id: str, user: dict, permission: str, lock: bool = False) -> OperationalShipment:
    require_permission(user, permission)
    org = organization_for_user(int(user["id"]))
    query = select(OperationalShipment).where(OperationalShipment.public_id == public_id, OperationalShipment.organization_id == org)
    if lock:
        query = query.with_for_update()
    row = db.session.scalar(query)
    if not row:
        raise OperationalError("ECONOMIC_SUBJECT_NOT_FOUND", "Economic subject was not found.", 404)
    return row


def _line(shipment: OperationalShipment, public_id: str, lock: bool = False) -> EconomicLine:
    query = select(EconomicLine).where(EconomicLine.public_id == public_id, EconomicLine.organization_id == shipment.organization_id, EconomicLine.operational_shipment_id == shipment.id)
    if lock:
        query = query.with_for_update()
    row = db.session.scalar(query)
    if not row:
        raise OperationalError("ECONOMIC_LINE_NOT_FOUND", "Economic line was not found.", 404)
    return row


def _permission(side: str, stage: str) -> str:
    if stage == "ACTUAL": return "economics.actual.create"
    if stage == "COMMITMENT": return "economics.commitment.create"
    return "economics.estimate.create"


def _audit(shipment, user, event, entity, correlation=None, details=None):
    db.session.add(EconomicAudit(organization_id=shipment.organization_id, operational_shipment_id=shipment.id, event_type=event, actor_user_id=user["id"], entity_public_id=entity.public_id, correlation_id=correlation, details=details or {}))


def serialize_observation(row: EconomicObservation) -> dict[str, Any]:
    binding = row.fx_binding
    return {"public_id": row.public_id, "stage": row.stage, "money": money_json(row.amount, row.currency), "effective_at": row.effective_at.isoformat(), "recorded_at": row.recorded_at.isoformat(), "authority": row.authority, "source": {"type": row.source_type, "public_id": row.source_public_id, "version": row.source_version}, "status": row.status, "correction_type": row.correction_type, "version": row.version, "reason": row.reason, "evidence": [{"public_id": item.public_id, "artifact_public_id": item.artifact_public_id, "artifact_version": item.artifact_version, "role": item.evidence_role, "associated_at": item.associated_at.isoformat()} for item in row.evidence_associations], "fx_binding": ({"public_id": binding.public_id, "fx_rate_public_id": binding.fx_rate_public_id, "fx_rate_version": binding.fx_rate_version, "from_currency": binding.from_currency, "to_currency": binding.to_currency, "rate": format(binding.rate, "f"), "rate_type": binding.rate_type, "effective_at": binding.effective_at.isoformat(), "authority": binding.authority, "source": binding.source, "bound_at": binding.bound_at.isoformat()} if binding else None)}


def serialize_line(row: EconomicLine, include_observations=True) -> dict[str, Any]:
    service = db.session.get(ServiceType, row.service_type_id)
    payload = {"public_id": row.public_id, "side": row.side, "service_public_id": service.public_id, "service_code": service.immutable_code, "service_title": service.en_name, "counterparty": ({"type": row.counterparty_type, "public_id": row.counterparty_public_id} if row.counterparty_public_id else None), "quantity": (format(row.quantity, "f") if row.quantity is not None else None), "uom_code": row.uom_code, "description": row.description, "lifecycle": row.lifecycle, "version": row.version, "created_at": row.created_at.isoformat()}
    if include_observations:
        payload["observations"] = [serialize_observation(o) for o in sorted(row.observations, key=lambda x: (x.recorded_at, x.id))]
    return payload


def create_line(shipment_id: str, payload: dict, user: dict) -> dict:
    side, stage = payload.get("side"), payload.get("stage")
    if side not in SIDES or stage not in STAGES:
        raise OperationalError("INVALID_ECONOMIC_CLASSIFICATION", "side and stage are invalid.")
    require_permission(user, _permission(side, stage))
    shipment = _shipment(shipment_id, user, "economics.revenue.view" if side == "REVENUE" else "economics.cost.view", lock=True)
    amount, currency = money(payload.get("money"))
    service = db.session.scalar(select(ServiceType).where(ServiceType.public_id == payload.get("service_public_id")))
    if not service or not service.is_active:
        raise OperationalError("INVALID_ECONOMIC_SERVICE", "An active governed service type is required.")
    key = str(payload.get("idempotency_key") or "")
    if not key or len(key) > 100:
        raise OperationalError("IDEMPOTENCY_KEY_REQUIRED", "A valid idempotency_key is required.")
    request_hash = _hash(payload)
    _lock_idempotency_scope(shipment.organization_id,"economics.create_line","OperationalShipment",shipment.id,key)
    existing = db.session.scalar(select(EconomicObservation).where(EconomicObservation.organization_id == shipment.organization_id, EconomicObservation.idempotency_key == key))
    if existing:
        if existing.request_hash != request_hash: raise OperationalError("IDEMPOTENCY_CONFLICT", "Idempotency key was used with another payload.", 409)
        return {"line": serialize_line(existing.line), "replayed": True}
    line = EconomicLine(organization_id=shipment.organization_id, operational_shipment_id=shipment.id, service_type_id=service.id, side=side, counterparty_type=(payload.get("counterparty") or {}).get("type"), counterparty_public_id=(payload.get("counterparty") or {}).get("public_id"), quantity=Decimal(str(payload["quantity"])) if payload.get("quantity") is not None else None, uom_code=payload.get("uom_code"), description=payload.get("description"), created_by_user_id=user["id"])
    db.session.add(line); db.session.flush()
    observation = EconomicObservation(organization_id=shipment.organization_id, line_id=line.id, stage=stage, amount=amount, currency=currency, effective_at=_time(payload.get("effective_at")), actor_user_id=user["id"], authority=str(payload.get("authority") or "").strip(), source_type=str(payload.get("source_type") or "MANUAL"), source_public_id=payload.get("source_public_id"), source_version=payload.get("source_version"), reason=payload.get("reason"), idempotency_key=key, request_hash=request_hash, correlation_id=payload.get("correlation_id"))
    if not observation.authority: raise OperationalError("AUTHORITY_REQUIRED", "Economic authority is required.")
    db.session.add(observation); db.session.flush(); _bind_fx(shipment, observation, payload.get("fx_rate_public_id")); _associate_evidence(shipment, observation, payload.get("evidence", []), user)
    _audit(shipment, user, "economic_observation.created", observation, observation.correlation_id, {"line_public_id": line.public_id, "side": side, "stage": stage})
    db.session.commit()
    return {"line": serialize_line(line), "replayed": False}


def append_observation(shipment_id: str, line_id: str, payload: dict, user: dict) -> dict:
    stage = payload.get("stage")
    if stage not in STAGES: raise OperationalError("INVALID_ECONOMIC_STAGE", "stage is invalid.")
    shipment = _shipment(shipment_id, user, _permission("", stage), lock=True); line = _line(shipment, line_id, lock=True)
    require_permission(user, "economics.revenue.view" if line.side == "REVENUE" else "economics.cost.view")
    expected_line_version = payload.get("expected_line_version")
    if expected_line_version is not None and line.version != expected_line_version:
        raise OperationalError("ECONOMIC_LINE_VERSION_CONFLICT", "Economic line is stale.", 409)
    if stage != "ACTUAL" and any(o.stage == stage and o.status == "AUTHORIZED" for o in line.observations):
        raise OperationalError("CORRECTION_REQUIRED", "A current observation exists; use the correction command.", 409)
    data = dict(payload, side=line.side, service_public_id=db.session.get(ServiceType, line.service_type_id).public_id)
    amount, currency = money(payload.get("money")); key=str(payload.get("idempotency_key") or ""); request_hash=_hash(data)
    _lock_idempotency_scope(shipment.organization_id,"economics.append_observation","EconomicLine",line.id,key)
    existing=db.session.scalar(select(EconomicObservation).where(EconomicObservation.organization_id==shipment.organization_id,EconomicObservation.idempotency_key==key))
    if existing:
        if existing.request_hash != request_hash: raise OperationalError("IDEMPOTENCY_CONFLICT","Idempotency key was used with another payload.",409)
        return {"observation":serialize_observation(existing),"replayed":True}
    row=EconomicObservation(organization_id=shipment.organization_id,line_id=line.id,stage=stage,amount=amount,currency=currency,effective_at=_time(payload.get("effective_at")),actor_user_id=user["id"],authority=str(payload.get("authority") or "").strip(),source_type=str(payload.get("source_type") or "MANUAL"),source_public_id=payload.get("source_public_id"),source_version=payload.get("source_version"),reason=payload.get("reason"),idempotency_key=key,request_hash=request_hash,correlation_id=payload.get("correlation_id"))
    if not key or not row.authority: raise OperationalError("VALIDATION_FAILED","idempotency_key and authority are required.")
    line.version += 1
    db.session.add(row);db.session.flush();_bind_fx(shipment,row,payload.get("fx_rate_public_id"));_associate_evidence(shipment,row,payload.get("evidence",[]),user);_audit(shipment,user,"economic_observation.created",row,row.correlation_id,{"line_public_id":line.public_id,"stage":stage});db.session.commit();return {"observation":serialize_observation(row),"replayed":False}


def correct(shipment_id: str, observation_id: str, payload: dict, user: dict) -> dict:
    shipment=_shipment(shipment_id,user,"economics.observation.correct",lock=True)
    old=db.session.scalar(select(EconomicObservation).join(EconomicLine).where(EconomicObservation.public_id==observation_id,EconomicObservation.organization_id==shipment.organization_id,EconomicLine.operational_shipment_id==shipment.id).with_for_update(of=EconomicObservation))
    if not old: raise OperationalError("ECONOMIC_OBSERVATION_NOT_FOUND","Economic observation was not found.",404)
    if old.status!="AUTHORIZED" or old.version!=payload.get("expected_version"): raise OperationalError("ECONOMIC_VERSION_CONFLICT","Observation is stale or already corrected.",409)
    kind=payload.get("correction_type")
    if kind not in {"SUPERSESSION","REVERSAL"}: raise OperationalError("INVALID_CORRECTION","Correction must be SUPERSESSION or REVERSAL.")
    if not str(payload.get("reason") or "").strip(): raise OperationalError("CORRECTION_REASON_REQUIRED","A correction reason is required.")
    amount,currency=(Decimal("0"),old.currency) if kind=="REVERSAL" else money(payload.get("money"))
    if kind=="SUPERSESSION" and currency!=old.currency: raise OperationalError("CURRENCY_CORRECTION_REQUIRES_NEW_LINE","Currency correction requires reversal and a new line.")
    key=str(payload.get("idempotency_key") or "");h=_hash(payload)
    _lock_idempotency_scope(shipment.organization_id,"economics.correct_observation","EconomicObservation",old.id,key)
    replay=db.session.scalar(select(EconomicObservation).where(EconomicObservation.organization_id==shipment.organization_id,EconomicObservation.idempotency_key==key))
    if replay:
        if replay.request_hash!=h: raise OperationalError("IDEMPOTENCY_CONFLICT","Idempotency key was used with another payload.",409)
        return {"observation":serialize_observation(replay),"replayed":True}
    old.status="REVERSED" if kind=="REVERSAL" else "SUPERSEDED";old.version+=1
    old.line.version += 1
    row=EconomicObservation(organization_id=old.organization_id,line_id=old.line_id,stage=old.stage,amount=amount,currency=currency,effective_at=_time(payload.get("effective_at")),actor_user_id=user["id"],authority=str(payload.get("authority") or "").strip(),source_type=str(payload.get("source_type") or "CORRECTION"),reason=payload["reason"],status="AUTHORIZED" if kind=="SUPERSESSION" else "REVERSED",correction_type=kind,corrects_observation_id=old.id,idempotency_key=key,request_hash=h,correlation_id=payload.get("correlation_id"))
    if not key or not row.authority: raise OperationalError("VALIDATION_FAILED","idempotency_key and authority are required.")
    db.session.add(row);db.session.flush();_bind_fx(shipment,row,payload.get("fx_rate_public_id"));_associate_evidence(shipment,row,payload.get("evidence",[]),user);_audit(shipment,user,"economic_observation.corrected",row,row.correlation_id,{"corrected_public_id":old.public_id,"correction_type":kind});db.session.commit();return {"observation":serialize_observation(row),"replayed":False}


def _bind_fx(shipment, observation, rate_public_id):
    if not rate_public_id:
        return
    rate = db.session.scalar(select(EconomicFxRate).where(EconomicFxRate.public_id == rate_public_id, EconomicFxRate.organization_id == shipment.organization_id).with_for_update())
    def aware(value): return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not rate or rate.status != "AUTHORIZED" or rate.from_currency != observation.currency or aware(rate.effective_at) > aware(observation.effective_at) or (rate.expires_at and aware(rate.expires_at) < aware(observation.effective_at)):
        raise OperationalError("FX_BINDING_INVALID", "The exact authorized FX fact is not applicable to this observation.", 409)
    db.session.add(EconomicObservationFx(organization_id=shipment.organization_id, observation_id=observation.id, fx_rate_id=rate.id, fx_rate_public_id=rate.public_id, fx_rate_version=rate.version, from_currency=rate.from_currency, to_currency=rate.to_currency, rate=rate.rate, rate_type=rate.rate_type, effective_at=rate.effective_at, authority=rate.authority, source=rate.source))


def _associate_evidence(shipment, observation, evidence, user):
    if not isinstance(evidence,list): raise OperationalError("INVALID_EVIDENCE","evidence must be a list.")
    for item in evidence:
        artifact=db.session.scalar(select(CaseDocumentFile).where(CaseDocumentFile.public_id==item.get("artifact_public_id"),CaseDocumentFile.shipment_request_id==shipment.shipment_request_id))
        if not artifact or artifact.status=="deleted" or artifact.version_number!=item.get("artifact_version"):
            raise OperationalError("ECONOMIC_EVIDENCE_NOT_FOUND","Exact eligible evidence was not found.",404)
        db.session.add(EconomicEvidenceAssociation(organization_id=shipment.organization_id,observation_id=observation.id,document_file_id=artifact.id,artifact_public_id=artifact.public_id,artifact_version=artifact.version_number,evidence_role=str(item.get("role") or "SUPPORTING"),associated_by_user_id=user["id"]))


def create_fx(payload: dict,user:dict)->dict:
    require_permission(user,"economics.fx.approve");org=organization_for_user(user["id"]);a,b=str(payload.get("from_currency") or "").upper(),str(payload.get("to_currency") or "").upper()
    if a not in CURRENCIES or b not in CURRENCIES or a==b: raise OperationalError("INVALID_FX_PAIR","FX currencies are invalid.")
    try: rate=Decimal(str(payload.get("rate")))
    except InvalidOperation as exc: raise OperationalError("INVALID_FX_RATE","FX rate is invalid.") from exc
    if rate<=0 or payload.get("rate_type") not in {"CONTRACTUAL","MANUAL_APPROVED"}: raise OperationalError("INVALID_FX_RATE","FX rate or type is invalid.")
    row=EconomicFxRate(organization_id=org,from_currency=a,to_currency=b,rate=rate,rate_type=payload["rate_type"],source=str(payload.get("source") or ""),authority=str(payload.get("authority") or ""),effective_at=_time(payload.get("effective_at")),expires_at=_time(payload["expires_at"],"expires_at") if payload.get("expires_at") else None,actor_user_id=user["id"])
    if not row.source or not row.authority: raise OperationalError("VALIDATION_FAILED","FX source and authority are required.")
    db.session.add(row);db.session.commit();return fx_json(row)


def fx_json(row): return {"public_id":row.public_id,"from_currency":row.from_currency,"to_currency":row.to_currency,"rate":format(row.rate,"f"),"rate_type":row.rate_type,"source":row.source,"authority":row.authority,"effective_at":row.effective_at.isoformat(),"expires_at":row.expires_at.isoformat() if row.expires_at else None,"status":row.status,"version":row.version}


def projection(shipment_id:str,user:dict,reporting_currency:str|None=None)->dict:
    shipment=_shipment(shipment_id,user,"economics.revenue.view");org=shipment.organization_id
    can_cost=True
    try: require_permission(user,"economics.cost.view")
    except OperationalError: can_cost=False
    lines=db.session.scalars(select(EconomicLine).where(EconomicLine.organization_id==org,EconomicLine.operational_shipment_id==shipment.id,EconomicLine.lifecycle=="ACTIVE")).all()
    target=(reporting_currency or "").upper() or None
    result={}
    for stage in ("ESTIMATE","COMMITMENT","ACTUAL"):
        sums={"REVENUE":Decimal(0),"COST":Decimal(0)};seen={"REVENUE":False,"COST":False};sources=[];missing=[];fx_used=[]
        for line in lines:
            if line.side=="COST" and not can_cost: continue
            current=[o for o in line.observations if o.stage==stage and o.status=="AUTHORIZED"]
            for obs in current:
                value=obs.amount
                basis=target or obs.currency
                if obs.currency!=basis:
                    binding=obs.fx_binding
                    if not binding or binding.from_currency != obs.currency or binding.to_currency != basis: missing.append("FX_MISSING");continue
                    value=(value*binding.rate).quantize(Decimal("0.000001"),rounding=ROUND_HALF_EVEN);fx_used.append(binding.fx_rate_public_id)
                sums[line.side]+=value;seen[line.side]=True;sources.append(obs.public_id)
        if not seen["REVENUE"]: missing.append("REVENUE_MISSING")
        if can_cost and not seen["COST"]: missing.append("COST_MISSING")
        currency=target or (next((o.currency for l in lines for o in l.observations if o.stage==stage and o.status=="AUTHORIZED"),None))
        mixed=not target and len({o.currency for l in lines for o in l.observations if o.stage==stage and o.status=="AUTHORIZED"})>1
        if mixed: missing.append("FX_MISSING")
        complete=not missing and can_cost
        margin=sums["REVENUE"]-sums["COST"] if complete else None
        result[stage]={"revenue":money_json(sums["REVENUE"],currency) if seen["REVENUE"] and not mixed else None,"cost":money_json(sums["COST"],currency) if seen["COST"] and can_cost and not mixed else None,"margin":money_json(margin,currency) if margin is not None else None,"margin_percentage":(format((margin/sums["REVENUE"]*100).quantize(Decimal("0.01")),"f") if margin is not None and sums["REVENUE"]!=0 else None),"currency":currency,"completeness":"COMPLETE" if complete else "INCOMPLETE","missing_inputs":sorted(set(missing + ([] if can_cost else ["COST_VISIBILITY_RESTRICTED"]))),"source_observation_ids":sources,"applied_fx_rate_ids":sorted(set(fx_used))}
    return {"shipment_public_id":shipment.public_id,"calculated_at":utcnow().isoformat(),"stages":result}


def list_lines(shipment_id,user):
    shipment=_shipment(shipment_id,user,"economics.revenue.view");perms=set()
    try: require_permission(user,"economics.cost.view");perms.add("cost")
    except OperationalError: pass
    rows=db.session.scalars(select(EconomicLine).where(EconomicLine.organization_id==shipment.organization_id,EconomicLine.operational_shipment_id==shipment.id).order_by(EconomicLine.created_at,EconomicLine.id)).all()
    return [serialize_line(r) for r in rows if r.side=="REVENUE" or "cost" in perms]


def quote_preview(shipment_id,user):
    shipment=_shipment(shipment_id,user,"economics.commitment.create");quote=db.session.get(ExpertQuote,shipment.accepted_quote_id)
    if not quote or quote.customer_response!="accepted": raise OperationalError("ACCEPTED_COMMERCIAL_INTENT_REQUIRED","An accepted quote is required.",409)
    source_identity=hashlib.sha256(f"accepted-quote|{shipment.public_id}|{quote.id}".encode()).hexdigest()
    exists=db.session.scalar(select(EconomicObservation).where(EconomicObservation.organization_id==shipment.organization_id,EconomicObservation.source_type=="ACCEPTED_QUOTE",EconomicObservation.source_public_id==source_identity))
    return {"shipment_public_id":shipment.public_id,"commercial_intent":{"amount":str(quote.amount),"currency":quote.currency,"accepted_at":quote.responded_at.isoformat() if quote.responded_at else None},"already_materialized":bool(exists),"confirmation_allowed":not bool(exists),"findings":[] if quote.currency in CURRENCIES else ["UNSUPPORTED_CURRENCY"]}


def quote_confirm(shipment_id,payload,user):
    preview=quote_preview(shipment_id,user)
    if preview["already_materialized"]: raise OperationalError("COMMERCIAL_INTENT_ALREADY_MATERIALIZED","Accepted quote was already materialized.",409)
    shipment=_shipment(shipment_id,user,"economics.revenue.view");quote=db.session.get(ExpertQuote,shipment.accepted_quote_id)
    source_identity=hashlib.sha256(f"accepted-quote|{shipment.public_id}|{quote.id}".encode()).hexdigest()
    command={"side":"REVENUE","stage":"COMMITMENT","service_public_id":payload.get("service_public_id"),"money":{"amount":str(quote.amount),"currency":quote.currency},"effective_at":quote.responded_at.replace(tzinfo=timezone.utc).isoformat() if quote.responded_at and quote.responded_at.tzinfo is None else quote.responded_at.isoformat(),"authority":payload.get("authority"),"source_type":"ACCEPTED_QUOTE","source_public_id":source_identity,"source_version":hashlib.sha256(f"{quote.id}|{quote.amount}|{quote.currency}|{quote.responded_at}".encode()).hexdigest(),"reason":payload.get("reason"),"idempotency_key":payload.get("idempotency_key"),"evidence":payload.get("evidence",[]),"correlation_id":payload.get("correlation_id"),"fx_rate_public_id":payload.get("fx_rate_public_id")}
    return create_line(shipment_id,command,user)


def project_projection(project_id,user,stage="COMMITMENT",reporting_currency=None):
    require_permission(user,"economics.revenue.view");org=organization_for_user(user["id"]);project=db.session.scalar(select(Project).where(Project.public_id==project_id,Project.organization_id==org))
    if not project: raise OperationalError("PROJECT_NOT_FOUND","Project was not found.",404)
    shipments=db.session.scalars(select(OperationalShipment).where(OperationalShipment.project_id==project.id,OperationalShipment.organization_id==org)).all();items=[projection(s.public_id,user,reporting_currency)["stages"][stage] for s in shipments]
    if not items:return {"project_public_id":project.public_id,"stage":stage,"completeness":"NOT_APPLICABLE","shipment_coverage":{"total":0,"complete":0},"revenue":None,"cost":None,"margin":None}
    complete=[x for x in items if x["completeness"]=="COMPLETE"]
    if len(complete)!=len(items):return {"project_public_id":project.public_id,"stage":stage,"completeness":"INCOMPLETE","shipment_coverage":{"total":len(items),"complete":len(complete)},"revenue":None,"cost":None,"margin":None,"missing_inputs":sorted({m for x in items for m in x["missing_inputs"]})}
    currency=items[0]["currency"]
    if any(x["currency"]!=currency for x in items):return {"project_public_id":project.public_id,"stage":stage,"completeness":"INCOMPLETE","shipment_coverage":{"total":len(items),"complete":len(complete)},"missing_inputs":["FX_MISSING"],"revenue":None,"cost":None,"margin":None}
    total=lambda key:sum(Decimal(x[key]["amount"]) for x in items)
    return {"project_public_id":project.public_id,"stage":stage,"completeness":"COMPLETE","shipment_coverage":{"total":len(items),"complete":len(items)},"revenue":money_json(total("revenue"),currency),"cost":money_json(total("cost"),currency),"margin":money_json(total("margin"),currency)}
