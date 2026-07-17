"""Deterministic CRUD/search rules for internal tracking checkpoint helpers."""
from __future__ import annotations

from backend.models import TrackingLocationReference
from backend.services.multi_unit_tracking_service import TrackingValidationError

LOCATION_TYPES = frozenset({"origin_city","commercial_hub","seaport","rail_terminal","road_terminal","border_point","transit_city","iran_gateway","destination_city","other"})
REFERENCE_STATUSES = frozenset({"internal_reference","verified_internal","inactive"})

def serialize(row, *, admin=False):
    payload={"id":row.id,"name_fa":row.name_fa,"name_en":row.name_en,"country_code":row.country_code,"location_type":row.location_type,"aliases":row.aliases or [],"is_active":row.is_active}
    if admin: payload.update({"internal_key":row.internal_key,"reference_status":row.reference_status,"sort_order":row.sort_order,"notes":row.notes})
    return payload

def search(*, query=None,country=None,location_type=None,include_inactive=False):
    q=TrackingLocationReference.query
    if not include_inactive: q=q.filter(TrackingLocationReference.is_active.is_(True))
    if country: q=q.filter(TrackingLocationReference.country_code==country.strip().upper())
    if location_type: q=q.filter(TrackingLocationReference.location_type==location_type)
    rows=q.order_by(TrackingLocationReference.sort_order,TrackingLocationReference.name_en,TrackingLocationReference.id).all()
    if not query or not query.strip(): return rows
    term=query.strip().casefold()
    return [row for row in rows if any(term in value.casefold() for value in [row.name_fa,row.name_en,*(row.aliases or [])] if value)]

def apply_fields(row,payload,*,creating=False):
    if creating:
        key=(payload.get("internal_key") or "").strip()
        if not key or len(key)>100: raise TrackingValidationError("valid internal_key is required")
        row.internal_key=key
    name=(payload.get("name_fa") if "name_fa" in payload else row.name_fa) or ""
    if not name.strip(): raise TrackingValidationError("name_fa is required")
    row.name_fa=name.strip()
    name_en=(payload.get("name_en") if "name_en" in payload else row.name_en) or None
    if name_en is not None:
        if not isinstance(name_en,str) or len(name_en.strip())>160: raise TrackingValidationError("name_en must be at most 160 characters")
        name_en=name_en.strip() or None
    row.name_en=name_en
    country=((payload.get("country_code") if "country_code" in payload else row.country_code) or "").strip().upper()
    if len(country)!=2 or not country.isalpha(): raise TrackingValidationError("country_code must be two letters")
    row.country_code=country
    kind=payload.get("location_type",row.location_type)
    if kind not in LOCATION_TYPES: raise TrackingValidationError("unsupported location_type")
    row.location_type=kind
    aliases=payload.get("aliases",row.aliases or [])
    if not isinstance(aliases,list) or any(not isinstance(x,str) for x in aliases): raise TrackingValidationError("aliases must be a string list")
    cleaned_aliases=[x.strip() for x in aliases if x.strip()]
    if any(len(x)>160 for x in cleaned_aliases): raise TrackingValidationError("aliases must be at most 160 characters")
    row.aliases=list(dict.fromkeys(cleaned_aliases))
    status=payload.get("reference_status",row.reference_status or "internal_reference")
    if status not in REFERENCE_STATUSES: raise TrackingValidationError("unsupported reference_status")
    row.reference_status=status
    order=payload.get("sort_order",row.sort_order or 0)
    if not isinstance(order,int) or isinstance(order,bool) or order<0: raise TrackingValidationError("sort_order must be non-negative")
    row.sort_order=order
    notes=(payload.get("notes") if "notes" in payload else row.notes) or None
    if notes is not None and not isinstance(notes,str): raise TrackingValidationError("notes must be text")
    row.notes=notes.strip() or None if notes is not None else None
    if "is_active" in payload:
        if not isinstance(payload["is_active"],bool): raise TrackingValidationError("is_active must be boolean")
        row.is_active=payload["is_active"]
        if not row.is_active: row.reference_status="inactive"
        elif row.reference_status=="inactive": row.reference_status="internal_reference"
    return row
