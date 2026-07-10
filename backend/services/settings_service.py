"""Service helpers for public and admin site settings."""
from typing import Any, Dict

from backend.extensions import db
from backend.models import SiteSetting

# Default values for all editable keys (used when DB has no value)
DEFAULT_SITE_SETTINGS = {
    "site_name": "فورواردرت",
    "site_tagline": "مسیر روشن درخواست حمل",
    "logo_url": "",
    "favicon_url": "",
    "page_title": "فورواردرت | ثبت و پیگیری درخواست حمل",
    "meta_description": "سرویس حرفه‌ای فورواردری و ارسال مرسوله در سراسر ایران. ارسال سریع، مطمئن و با بیمه کامل.",
    "meta_author": "فورواردری سریع",
    "meta_keywords": "فورواردری, ارسال مرسوله, حمل و نقل, ارسال سریع, ایران",
    "footer_company_name": "فورواردری سریع",
    "footer_description": "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور",
    "footer_phone": "۰۲۱-۸۸۷۷۶۶۵۵",
    "footer_email": "info@forwarding.ir",
    "footer_address": "تهران، میدان آزادی",
    "footer_working_hours_1": "شنبه تا چهارشنبه: ۸-۱۸",
    "footer_working_hours_2": "پنج‌شنبه: ۸-۱۶",
    "footer_support_text": "پشتیبانی ۲۴ ساعته",
    "footer_copyright": "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است.",
    "footer_contact_title": "اطلاعات تماس",
    "footer_hours_title": "ساعات کاری",
    "nav_about": "درباره ما",
    "nav_contact": "تماس با ما",
    "nav_crm": "CRM",
    "nav_admin": "پنل ادمین",
    "btn_expert_login": "ورود",
    "page_about_content": "",
    "page_contact_content": "",
    "hero_title_1": "ارسال سریع و مطمئن",
    "hero_title_2": "با انواع روش‌های حمل",
    "hero_subtitle": "با سرویس فورواردری ما، بسته‌های خود را از طریق جاده، ریل، دریا یا ترکیبی از این روش‌ها ارسال کنید",
    "hero_feature_1": "ارسال فوری",
    "hero_feature_2": "۲۴ ساعته",
    "hero_feature_3": "بیمه شده",
    "hero_feature_4": "کیفیت بالا",
    "index_services_title": "خدمات فورواردر",
    "index_services_subtitle": "درخواست ارسال مرسوله یا پیگیری درخواست‌های قبلی",
    "index_tab_request": "درخواست ارسال",
    "index_tab_track": "پیگیری درخواست",
    "index_track_title": "پیگیری درخواست",
    "index_track_label": "شماره پیگیری",
    "index_shipping_type_title": "نوع ارسال خود را انتخاب کنید",
}


def get_default_settings() -> Dict[str, str]:
    """Return editable site setting defaults."""
    return dict(DEFAULT_SITE_SETTINGS)


def merge_settings_with_defaults(stored_settings: Dict[str, str]) -> Dict[str, str]:
    """Return default settings merged with stored values."""
    result = get_default_settings()
    for key, value in stored_settings.items():
        result[key] = value
    return result


def get_public_settings() -> Dict[str, str]:
    """Return merged public site settings."""
    rows = db.session.query(SiteSetting).all()
    db_map = {row.key: (row.value or "") for row in rows}
    return merge_settings_with_defaults(db_map)


def get_admin_settings() -> Dict[str, str]:
    """Return merged site settings for the admin form."""
    return get_public_settings()


def is_settings_payload(payload: Any) -> bool:
    """Return whether the admin update body is a settings object."""
    return isinstance(payload, dict)


def normalize_settings_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only editable keys while preserving current value coercion behavior."""
    allowed_keys = set(DEFAULT_SITE_SETTINGS.keys())
    return {
        key: value if value is None else str(value)
        for key, value in payload.items()
        if key in allowed_keys
    }


def update_settings(payload: Dict[str, Any]) -> Dict[str, str]:
    """Persist editable site settings and return the merged settings payload."""
    normalized = normalize_settings_payload(payload)
    for key, value in normalized.items():
        row = db.session.query(SiteSetting).get(key)
        if row:
            row.value = value
        else:
            db.session.add(SiteSetting(key=key, value=value))
    db.session.commit()
    return get_admin_settings()


def rollback_settings_update() -> None:
    """Rollback a failed settings update transaction."""
    db.session.rollback()
