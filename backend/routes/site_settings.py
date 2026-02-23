"""Public and upload routes for site settings (no auth for GET settings and serving logo)."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, jsonify, current_app, send_from_directory

from backend.models import SiteSettings
from backend.extensions import db

site_settings_bp = Blueprint("site_settings", __name__, url_prefix="/api")


def _get_settings_row():
    """Return the singleton SiteSettings row; None if not yet migrated."""
    return db.session.query(SiteSettings).get(1)


def _settings_to_dict(row: SiteSettings | None) -> dict:
    if not row:
        return {
            "company_name": "فورواردری سریع",
            "tagline": "ارسال آسان و مطمئن",
            "footer_description": "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور",
            "contact_phone": "۰۲۱-۸۸۷۷۶۶۵۵",
            "contact_email": "info@forwarding.ir",
            "contact_address": "تهران، میدان آزادی",
            "working_hours_weekdays": "شنبه تا چهارشنبه: ۸-۱۸",
            "working_hours_thursday": "پنج‌شنبه: ۸-۱۶",
            "support_text": "پشتیبانی ۲۴ ساعته",
            "copyright_text": "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است.",
            "logo_url": None,
        }
    return {
        "company_name": row.company_name or "فورواردری سریع",
        "tagline": row.tagline or "",
        "footer_description": row.footer_description or "",
        "contact_phone": row.contact_phone or "",
        "contact_email": row.contact_email or "",
        "contact_address": row.contact_address or "",
        "working_hours_weekdays": row.working_hours_weekdays or "",
        "working_hours_thursday": row.working_hours_thursday or "",
        "support_text": row.support_text or "",
        "copyright_text": row.copyright_text or "",
        "logo_url": row.logo_url,
    }


@site_settings_bp.get("/site-settings")
def get_site_settings():
    """Public endpoint: return current site settings for header/footer. No auth."""
    try:
        row = _get_settings_row()
        data = _settings_to_dict(row)
        return jsonify(data)
    except Exception as e:
        current_app.logger.exception("get_site_settings: %s", e)
        return jsonify(_settings_to_dict(None))


def get_uploads_folder():
    """Return the instance uploads directory, creating it if needed."""
    folder = Path(current_app.instance_path) / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@site_settings_bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    """Serve uploaded site logo. Only allow site_logo.* for security."""
    if not filename.startswith("site_logo."):
        return jsonify({"error": "Not found"}), 404
    uploads = get_uploads_folder()
    path = uploads / filename
    if not path.is_file() or path.resolve().parent != uploads.resolve():
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(uploads, filename, max_age=3600)
