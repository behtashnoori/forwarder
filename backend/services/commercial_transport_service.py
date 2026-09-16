"""Commercial request intent contract; never an operational route builder."""
from copy import deepcopy

from backend.extensions import db
from backend.models import TransportMethod


class ShipmentValidationError(ValueError):
    def __init__(self, message, status_code=400, code="VALIDATION_FAILED", field=None):
        super().__init__(message)
        self.message, self.status_code, self.code = message, status_code, code
        self.field = field


LABELS = {"road": "جاده‌ای", "rail": "ریلی", "air": "هوایی", "sea": "دریایی"}
# Exact names whose semantics are documented by seed_transport_methods.py.
ALIASES = {
    "road": "road", "road transport": "road", "land transport": "road",
    "rail": "rail", "rail transport": "rail",
    "air": "air", "air transport": "air", "air freight": "air",
    "sea": "sea", "sea freight": "sea",
}
SCOPES = {"transport_method": "عمومی", "international_transport_method": "بین‌المللی",
          "domestic_transport_method": "داخلی"}


def fail(code, message, field="transport_intent"):
    raise ShipmentValidationError(message, code=code, field=field)


def active_methods():
    return db.session.query(TransportMethod).filter_by(is_active=True).order_by(TransportMethod.id).all()


def mode_for(value):
    return ALIASES.get(value.strip().casefold()) if isinstance(value, str) else None


def intent_options():
    grouped = {}
    for row in active_methods():
        mode = mode_for(row.name)
        if mode:
            grouped.setdefault(mode, {"mode": mode, "label": LABELS[mode], "catalog_ids": []})["catalog_ids"].append(row.id)
    return list(grouped.values())


def normalize_transport(payload, *, new_contract=False):
    if "transport_sequence" in payload:
        fail("UNSUPPORTED_TRANSPORT_FIELD", "از فیلد transport_intent استفاده کنید.", "transport_sequence")
    strict = new_contract or "transport_intent" in payload
    preference = payload.get("transport_method_preference", "customer_choice")
    if preference not in ("customer_choice", "forwarder_suggestion"):
        if strict:
            fail("INVALID_TRANSPORT_PREFERENCE", "نوع انتخاب روش حمل نامعتبر است.", "transport_method_preference")
        preference = "customer_choice"  # established legacy default
    scalars = {}
    for key in SCOPES:
        value = payload.get(key)
        if key == "transport_method" and not value:
            value = payload.get("shipment_mode")  # established legacy alias
        if value is None or value == "":
            scalars[key] = None
            continue
        if not isinstance(value, str):
            fail("INVALID_TRANSPORT_REFERENCE", "روش حمل نامعتبر است.", key)
        value = value.strip()
        if value and not mode_for(value) and not any(row.name.casefold() == value.casefold() for row in active_methods()):
            fail("INVALID_TRANSPORT_REFERENCE", "روش حمل در فهرست معتبر نیست.", key)
        scalars[key] = (value.lower() if key == "transport_method" else value) or None
    intent = payload.get("transport_intent")
    if intent is None:
        if strict and preference == "customer_choice":
            fail("TRANSPORT_INTENT_REQUIRED", "توالی روش‌های حمل را انتخاب کنید.")
    else:
        if not isinstance(intent, dict) or set(intent) != {"version", "steps"}:
            fail("INVALID_TRANSPORT_INTENT", "ساختار توالی روش‌های حمل نامعتبر است.")
        if type(intent["version"]) is not int or intent["version"] != 1:
            fail("UNSUPPORTED_TRANSPORT_VERSION", "نسخه توالی روش‌های حمل پشتیبانی نمی‌شود.")
        steps = intent["steps"]
        if not isinstance(steps, list) or not steps:
            fail("INVALID_TRANSPORT_INTENT", "حداقل یک روش حمل انتخاب کنید.")
        available = {item["mode"] for item in intent_options()}
        for step in steps:
            if not isinstance(step, dict) or set(step) != {"mode"} or not isinstance(step["mode"], str):
                fail("INVALID_TRANSPORT_INTENT", "ساختار مرحله حمل نامعتبر است.")
            if step["mode"] not in LABELS:
                fail("UNSUPPORTED_TRANSPORT_MODE", "روش حمل پشتیبانی نمی‌شود.")
            if step["mode"] not in available:
                fail("TRANSPORT_MODE_UNAVAILABLE", "روش حمل انتخاب‌شده اکنون فعال نیست.")
        distinct = {step["mode"] for step in steps}
        classification = "combined" if len(distinct) > 1 else "single-mode"
        selected = payload.get("transport_classification")
        if selected is not None and selected != classification:
            fail("TRANSPORT_CLASSIFICATION_MISMATCH", "حمل ترکیبی به حداقل دو روش متفاوت نیاز دارد؛ نوع انتخاب را بررسی کنید.", "transport_classification")
        for key, value in scalars.items():
            if value and (mode_for(value) not in distinct or (key == "transport_method" and len(distinct) != 1)):
                fail("TRANSPORT_INPUT_CONFLICT", "روش حمل قدیمی با توالی انتخاب‌شده سازگار نیست.", key)
    if intent is None and payload.get("transport_classification") is not None:
        fail("TRANSPORT_CLASSIFICATION_MISMATCH", "ابتدا توالی حمل را مشخص کنید.", "transport_classification")
    return {**scalars, "transport_method_preference": preference, "transport_intent": deepcopy(intent)}


def project_transport(source):
    get = source.get if isinstance(source, dict) else lambda key: getattr(source, key, None)
    intent = deepcopy(get("transport_intent"))
    legacy = [{"field": key, "scope": scope, "value": get(key),
               "label": LABELS.get(mode_for(get(key)), get(key))}
              for key, scope in SCOPES.items() if get(key)]
    if intent is not None:
        modes = [step["mode"] for step in intent["steps"]]
        classification = "combined" if len(set(modes)) > 1 else "single-mode"
        steps = [{"mode": mode, "label": LABELS.get(mode, mode)} for mode in modes]
        display = " ← ".join(step["label"] for step in steps)
    else:
        classification, steps = None, []
        display = "؛ ".join(f'{item["scope"]}: {item["label"]}' for item in legacy)
        if not display:
            display = "پیشنهاد فورواردر" if get("transport_method_preference") == "forwarder_suggestion" else "ثبت نشده"
    return {"transport_intent": intent, "transport_summary": {
        "classification": classification, "steps": steps, "display": display,
        "legacy_scopes": legacy, "legacy_display_limited": classification == "combined",
        "meaning": "customer_intent_not_operational_route",
    }}


def reject_transport_update(payload):
    keys = set(SCOPES) | {"shipment_mode", "transport_intent", "transport_sequence", "transport_classification", "transport_method_preference"}
    if keys.intersection(payload):
        fail("TRANSPORT_UPDATE_NOT_SUPPORTED", "این عملیات امکان تغییر خواسته حمل را ندارد.")
