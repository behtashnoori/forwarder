"""Small read-time Persian catalog for ADR-046; no database presentation state."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
import unicodedata


class AttentionLevel(str, Enum):
    URGENT = "URGENT"
    FOLLOW_UP = "FOLLOW_UP"
    REVIEW = "REVIEW"


class Semantic(str, Enum):
    ACTIVE_DELAY = "delay_open"
    ACTIVE_EXCEPTION = "exception_open"
    CHECKPOINT_FOLLOW_UP = "route_follow_up"
    DEPENDENCY_BLOCKED = "continuation_blocked"
    REPLAN_REQUIRED = "route_replan"
    OVERDUE_MILESTONE_FOLLOW_UP = "stage_confirmation_follow_up"
    READINESS_BLOCKED = "documents_blocked"
    READINESS_REVIEW = "document_need_review"


# Only governed display fields may call this guard. It does not make arbitrary
# notes/evidence safe. Conservative rejection includes values embedded in labels.
_PROTECTED = re.compile(
    r"مالی|پرداخت|درآمد|هزینه|سود|زیان|حاشیه|مبلغ|قیمت|ارزش|نرخ|بدهی|طلب|ارز|ریال|تومان|دلار|یورو|"
    r"محرمانه|خصوصی|حساب|بانک|فاکتور|صورتحساب|حقوق|اعتبار مالی"
)


def safe_display_label(value):
    if not isinstance(value, str):
        return None
    value = unicodedata.normalize("NFKC", value).strip().replace("ي", "ی").replace("ك", "ک")
    if (not value or len(value) > 160 or _PROTECTED.search(value)
            or not re.search(r"[\u0621-\u06ff]", value)
            or any(not (c.isalpha() and "\u0621" <= c <= "\u06ff"
                        or c in " \u200c()-،") for c in value)):
        return None
    return " ".join(value.split())


def utc(value):
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@dataclass(frozen=True)
class TimeContext:
    kind: str
    label: str
    at: datetime


_TIME_LABELS = {
    "delay_start": "شروع تأخیر",
    "exception_occurrence": "ثبت وقوع مشکل",
    "expected_due": "زمان مورد انتظار",
    "work_open": "پیگیری باز از",
    "evaluated": "بررسی‌شده در",
}


def time_context(kind, value):
    at = utc(value)
    return TimeContext(kind, _TIME_LABELS[kind], at) if at else None


_CATALOG = {
    Semantic.ACTIVE_DELAY: ("تأخیر محموله هنوز برطرف نشده است", "برای این محموله تأخیر باز ثبت شده است."),
    Semantic.ACTIVE_EXCEPTION: ("یک مشکل عملیاتی هنوز برطرف نشده است", "این مورد هنوز در پرونده محموله باز است."),
    Semantic.CHECKPOINT_FOLLOW_UP: ("پیگیری یکی از نقاط مسیر هنوز باز است", "برای این نقطه، پیگیری عبور از زمان برنامه ثبت شده است."),
    Semantic.DEPENDENCY_BLOCKED: ("پیگیری مانع ادامه مسیر هنوز باز است", "پیگیری تکمیل مرحله قبلی برای ادامه مسیر ثبت شده است."),
    Semantic.REPLAN_REQUIRED: ("پیگیری بازبینی برنامه مسیر هنوز باز است", "به‌دلیل تأخیر ثبت‌شده، بازبینی برنامه مسیر درخواست شده است."),
    Semantic.OVERDUE_MILESTONE_FOLLOW_UP: ("پیگیری تأیید یکی از مراحل هنوز باز است", "برای این مرحله، پیگیری عبور از زمان برنامه و تأیید نشدن ثبت شده است."),
    Semantic.READINESS_BLOCKED: ("مدارک لازم برای مرحله بعد آماده نیست", "یک مانع مربوط به مدارک برای ادامه این مرحله وجود دارد."),
    Semantic.READINESS_REVIEW: ("لزوم ارائه یکی از مدارک باید بررسی شود", "لزوم ارائه این سند هنوز مشخص نشده است."),
}
_BLOCKERS = {
    "DOC_ARTIFACT_MISSING": "سند {label} در دسترس نیست.",
    "DOC_ARTIFACT_REJECTED": "سند {label} رد شده است.",
    "DOC_ARTIFACT_SUPERSEDED": "نسخه مرتبط سند {label} دیگر معتبر نیست.",
    "DOC_APPROVAL_REQUIRED": "سند {label} هنوز تأیید نشده است.",
    "DOC_VERIFICATION_REQUIRED": "بررسی اعتبار سند {label} کامل نشده است.",
    "DOC_REQUIREMENT_UNRESOLVED": "هنوز مشخص نشده است که سند {label} برای این مرحله لازم است یا نه.",
}
SUPPORTED_BLOCKERS = frozenset(_BLOCKERS)
URGENT_EXPLANATION = "این مورد در ارزیابی فعلی، نیازمند رسیدگی فوری شناخته شده است."
EMPTY_MESSAGE = "در حال حاضر موردی برای پیگیری در برج کنترل نمایش داده نمی‌شود."
UNAVAILABLE_MESSAGE = "بررسی موارد نیازمند توجه کامل نشد. دوباره تلاش کنید."
_ATTENTION_LABELS = {
    AttentionLevel.URGENT: "اقدام فوری",
    AttentionLevel.FOLLOW_UP: "نیازمند پیگیری",
    AttentionLevel.REVIEW: "نیازمند بررسی",
}
# Existing product transport labels; operational handling/transfer is not a
# Shipment transport mode. Combined transport is read-time presentation only.
_TRANSPORT_LABELS = {"road": "جاده‌ای", "rail": "ریلی", "sea": "دریایی", "air": "هوایی"}
_COMBINED_TRANSPORT_LABEL = "ترکیبی"


def attention_label(level):
    return _ATTENTION_LABELS[level]


def transport_label(mode):
    return _TRANSPORT_LABELS.get(mode)


def transport_modes_label(modes):
    """Translate known actual modes only; the caller validates route continuity."""
    modes = frozenset(modes)
    if not modes or not modes.issubset(_TRANSPORT_LABELS):
        return None
    if len(modes) == 1:
        return transport_label(next(iter(modes)))
    return _COMBINED_TRANSPORT_LABEL


def translate(semantic, *, label=None, checkpoint_type=None):
    title, explanation = _CATALOG[semantic]
    label = safe_display_label(label)
    if label:
        if semantic == Semantic.ACTIVE_DELAY:
            explanation = f"دلیل ثبت‌شده برای تأخیر: {label}."
        elif semantic == Semantic.ACTIVE_EXCEPTION:
            title = f"{label} هنوز برطرف نشده است"
        elif semantic == Semantic.CHECKPOINT_FOLLOW_UP:
            if checkpoint_type in {"border_exit", "border_entry", "transit_border_entry", "transit_border_exit"}:
                point = f"عبور از نقطه مرزی {label}"
            elif checkpoint_type in {"export_customs", "import_customs"}:
                point = f"مرحله گمرکی {label}"
            else:
                point = f"نقطه {label}"
            title = f"پیگیری {point} هنوز باز است"
        elif semantic == Semantic.OVERDUE_MILESTONE_FOLLOW_UP:
            title = f"پیگیری تأیید {label} هنوز باز است"
    return title, explanation


def translate_blocker(code, label=None):
    if code not in SUPPORTED_BLOCKERS:
        raise ValueError("Unsupported readiness category")
    label = safe_display_label(label)
    if label:
        return _BLOCKERS[code].format(label=label)
    semantic = Semantic.READINESS_REVIEW if code == "DOC_REQUIREMENT_UNRESOLVED" else Semantic.READINESS_BLOCKED
    return _CATALOG[semantic][1]
