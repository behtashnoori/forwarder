"""Public and admin routes for site-wide editable settings."""
from flask import Blueprint, jsonify, request, send_file
from backend.services.admin_authorization_service import require_platform_admin
from backend.services import settings_service, upload_service

# Public blueprint: no auth
site_bp = Blueprint("site", __name__, url_prefix="/api")


@site_bp.get("/site-settings")
def get_site_settings():
    """Return all site settings (public). Frontend uses this for header, footer, etc."""
    return jsonify(settings_service.get_public_settings())


# Admin blueprint: requires admin
admin_site_bp = Blueprint("admin_site", __name__, url_prefix="/api/admin")


@admin_site_bp.get("/site-settings")
@require_platform_admin()
def admin_get_site_settings():
    """Return all site settings for admin form."""
    return jsonify(settings_service.get_admin_settings())


@admin_site_bp.put("/site-settings")
@require_platform_admin()
def admin_update_site_settings():
    """Update site settings. Body: { "key1": "value1", ... }."""
    try:
        data = request.get_json() or {}
        if not settings_service.is_settings_payload(data):
            return jsonify({"error": "بدنه درخواست باید آبجکت باشد"}), 400
        return jsonify(settings_service.update_settings(data))
    except Exception:
        settings_service.rollback_settings_update()
        return jsonify({"error": "خطا در ذخیره تنظیمات"}), 500


@admin_site_bp.post("/upload")
@require_platform_admin()
def admin_upload_logo():
    """Accept a single image file (logo), save to instance/uploads, return public URL."""
    if "file" not in request.files and "logo" not in request.files:
        return jsonify({"error": "فایلی ارسال نشده است"}), 400
    file = request.files.get("file") or request.files.get("logo")
    url, error = upload_service.save_logo_upload(file)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"url": url})


@site_bp.get("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve an uploaded file by filename. Disallow path traversal."""
    if not upload_service.is_valid_uploaded_filename(filename):
        return jsonify({"error": "نام فایل نامعتبر است"}), 400
    if not upload_service.uploaded_file_exists(filename):
        return jsonify({"error": "فایل یافت نشد"}), 404
    path = upload_service.uploaded_file_path(filename)
    mime = upload_service.uploaded_file_mime_type(filename)
    return send_file(path, mimetype=mime, as_attachment=False)
