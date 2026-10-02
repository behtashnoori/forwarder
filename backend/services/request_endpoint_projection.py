"""Read-only source identities for explicit Request-to-operation review.

No resolver is called: reading a Request must never create CanonicalLocation rows.
Labels use current reference names, not invented historical snapshots.
"""
from backend.extensions import db
from backend.models import City, Country, Province, InternationalCity, IranPort, CustomsOffice
from backend.services.geography_presentation import name_fa
from backend.services.location_resolver import _eligible


def endpoints(req):
    result = {}
    for side, prefix in (("origin", "origin"), ("destination", "dest")):
        row = db.session.get(City, getattr(req, prefix + "_city_id")) if getattr(req, prefix + "_city_id") else None
        kind = "city"
        if row is None and getattr(req, prefix + "_international_city_id"):
            row = db.session.get(InternationalCity, getattr(req, prefix + "_international_city_id"))
            kind = "international_city"
        if row is None and side == "destination" and req.iran_dest_type:
            model, identity, kind = {
                "city": (City, req.iran_dest_city_id, "city"),
                "port": (IranPort, req.iran_entry_port_id, "iran_port"),
                "customs": (CustomsOffice, req.iran_dest_customs_office_id, "customs_office"),
            }.get(req.iran_dest_type, (None, None, None))
            row = db.session.get(model, identity) if model and identity else None
        if row is None and req.shipping_type != "international" and getattr(req, prefix + "_province_id"):
            row = db.session.get(Province, getattr(req, prefix + "_province_id"))
            kind = "province"
        region = row if kind == "province" else db.session.get(Province, row.province_id) if row and getattr(row, "province_id", None) else None
        country_id = getattr(row, "country_id", None) or (region.country_id if region else None) or getattr(req, prefix + "_country_id")
        country = db.session.get(Country, country_id) if country_id else None
        label = " · ".join(dict.fromkeys(value for value in [(name_fa(row) if hasattr(row, "geoname_id") else row.name_fa or row.name_en) if row else getattr(req, prefix + "_city_international"), name_fa(region) if region else None, country.name_fa if country else None] if value))
        result[side] = {"label": label or "جزئیات محل درخواست در دسترس نیست",
            "reference": {"source_type": kind, "source_id": row.id, "country_id": country_id,
                          "display_label": label} if row and country_id else None,
            "reusable": bool(row and country and _eligible(row) and _eligible(country) and (not region or _eligible(region))),
            "province_id": region.id if region else None,
            "country_id": country_id}
    return result
