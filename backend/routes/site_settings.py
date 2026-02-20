"""Public API for site-wide settings (brand, contact, footer) for use in Header/Footer."""
from flask import Blueprint, jsonify

from backend.models import SiteSetting
from backend.extensions import db

site_settings_bp = Blueprint("site_settings", __name__, url_prefix="/api")


@site_settings_bp.get("/site-settings")
def get_site_settings():
    """Return all site settings as key-value dict (public, no auth)."""
    rows = db.session.query(SiteSetting.key, SiteSetting.value).all()
    return jsonify({r.key: r.value for r in rows})
