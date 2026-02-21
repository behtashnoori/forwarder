"""Public and admin routes for site-wide editable settings."""
from flask import Blueprint, jsonify, request
from backend.extensions import db
from backend.models import SiteSetting
from backend.security import require_role

# Default values for all editable keys (used when DB has no value)
DEFAULT_SITE_SETTINGS = {
    "site_name": "فورواردری سریع",
    "site_tagline": "ارسال آسان و مطمئن",
    "logo_url": "",
    "favicon_url": "",
    "page_title": "فورواردری سریع - ارسال آسان و مطمئن در سراسر کشور",
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
    "btn_expert_login": "ورود کارشناس",
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


def _get_all_settings():
    """Return merged default + DB settings as a flat dict."""
    rows = db.session.query(SiteSetting).all()
    db_map = {r.key: (r.value or "") for r in rows}
    result = dict(DEFAULT_SITE_SETTINGS)
    for k, v in db_map.items():
        if k in result:
            result[k] = v
        else:
            result[k] = v
    return result


# Public blueprint: no auth
site_bp = Blueprint("site", __name__, url_prefix="/api")


@site_bp.get("/site-settings")
def get_site_settings():
    """Return all site settings (public). Frontend uses this for header, footer, etc."""
    return jsonify(_get_all_settings())


# Admin blueprint: requires admin
admin_site_bp = Blueprint("admin_site", __name__, url_prefix="/api/admin")


@admin_site_bp.get("/site-settings")
@require_role("admin")
def admin_get_site_settings():
    """Return all site settings for admin form."""
    return jsonify(_get_all_settings())


@admin_site_bp.put("/site-settings")
@require_role("admin")
def admin_update_site_settings():
    """Update site settings. Body: { "key1": "value1", ... }."""
    try:
        data = request.get_json() or {}
        if not isinstance(data, dict):
            return jsonify({"error": "بدنه درخواست باید آبجکت باشد"}), 400
        allowed_keys = set(DEFAULT_SITE_SETTINGS.keys())
        for key, value in data.items():
            if key not in allowed_keys:
                continue
            str_value = value if value is None else str(value)
            row = db.session.query(SiteSetting).get(key)
            if row:
                row.value = str_value
            else:
                db.session.add(SiteSetting(key=key, value=str_value))
        db.session.commit()
        return jsonify(_get_all_settings())
    except Exception:
        db.session.rollback()
        return jsonify({"error": "خطا در ذخیره تنظیمات"}), 500
