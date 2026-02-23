"""Public and admin routes for site-wide editable settings."""
import os
import re
import uuid
from flask import Blueprint, jsonify, request, current_app, send_file
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
    "btn_expert_login": "ورود",
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

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _upload_dir():
    """Return the directory for uploaded files (e.g. logo). Creates if missing."""
    d = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(d, exist_ok=True)
    return d


def _allowed_file(filename):
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    return ext in ALLOWED_EXTENSIONS


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


@admin_site_bp.post("/upload")
@require_role("admin")
def admin_upload_logo():
    """Accept a single image file (logo), save to instance/uploads, return public URL."""
    if "file" not in request.files and "logo" not in request.files:
        return jsonify({"error": "فایلی ارسال نشده است"}), 400
    file = request.files.get("file") or request.files.get("logo")
    if not file or not file.filename:
        return jsonify({"error": "فایلی انتخاب نشده است"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": "فرمت فایل مجاز نیست. فقط تصویر (png, jpg, gif, webp, svg)"}), 400
    content = file.read()
    if len(content) > MAX_LOGO_SIZE_BYTES:
        return jsonify({"error": "حجم فایل بیش از حد مجاز است (حداکثر ۵ مگابایت)"}), 400
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    safe_name = f"logo-{uuid.uuid4().hex[:12]}.{ext}"
    upload_dir = _upload_dir()
    path = os.path.join(upload_dir, safe_name)
    with open(path, "wb") as f:
        f.write(content)
    # Return path-only URL so frontend can prepend its API base (works with proxy and different origins)
    url = f"/api/uploads/{safe_name}"
    return jsonify({"url": url})


@site_bp.get("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve an uploaded file by filename. Disallow path traversal."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "نام فایل نامعتبر است"}), 400
    if not re.match(r"^[a-zA-Z0-9_.-]+$", filename):
        return jsonify({"error": "نام فایل نامعتبر است"}), 400
    upload_dir = _upload_dir()
    path = os.path.join(upload_dir, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "فایل یافت نشد"}), 404
    mime = "application/octet-stream"
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}" if ext != "jpg" else "image/jpeg"
    return send_file(path, mimetype=mime, as_attachment=False)
