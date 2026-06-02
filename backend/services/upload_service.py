"""Service helpers for site settings upload behavior."""
import os
import re
import uuid
from typing import Optional, Tuple

from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def upload_dir() -> str:
    """Return the directory for uploaded files (e.g. logo). Creates if missing."""
    directory = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(directory, exist_ok=True)
    return directory


def allowed_file(filename: str) -> bool:
    """Return whether the filename extension is accepted for logo uploads."""
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    return ext in ALLOWED_EXTENSIONS


def save_logo_upload(file) -> Tuple[Optional[str], Optional[str]]:
    """Validate and save a logo upload, returning (url, error_message)."""
    if not file or not file.filename:
        return None, "فایلی انتخاب نشده است"
    if not allowed_file(file.filename):
        return None, "فرمت فایل مجاز نیست. فقط تصویر (png, jpg, gif, webp, svg)"

    content = file.read()
    if len(content) > MAX_LOGO_SIZE_BYTES:
        return None, "حجم فایل بیش از حد مجاز است (حداکثر ۵ مگابایت)"

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    safe_name = f"logo-{uuid.uuid4().hex[:12]}.{ext}"
    path = os.path.join(upload_dir(), safe_name)
    with open(path, "wb") as output_file:
        output_file.write(content)

    # Return path-only URL so frontend can prepend its API base (works with proxy and different origins)
    return f"/api/uploads/{safe_name}", None


def is_valid_uploaded_filename(filename: str) -> bool:
    """Return whether an uploaded filename is safe to serve."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_.-]+$", filename))


def uploaded_file_path(filename: str) -> str:
    """Return the filesystem path for an uploaded filename."""
    return os.path.join(upload_dir(), filename)


def uploaded_file_exists(filename: str) -> bool:
    """Return whether an uploaded filename exists on disk."""
    return os.path.isfile(uploaded_file_path(filename))


def uploaded_file_mime_type(filename: str) -> str:
    """Return the current mimetype for an uploaded file."""
    mime = "application/octet-stream"
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}" if ext != "jpg" else "image/jpeg"
    return mime
