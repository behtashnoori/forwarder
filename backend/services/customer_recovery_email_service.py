"""Narrow SMTP adapter for Customer Portal password-recovery email."""
from __future__ import annotations

import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Mapping
from urllib.parse import urlencode

from flask import current_app


DELIVERY_SENT = "SENT"
DELIVERY_FAILED = "FAILED"
DELIVERY_SUPPRESSED = "SUPPRESSED"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def validate_recovery_email_configuration(config: Mapping[str, Any]) -> None:
    """Fail closed for an explicitly enabled Production SMTP adapter."""
    enabled = _as_bool(config.get("CUSTOMER_RECOVERY_EMAIL_ENABLED"))
    production = str(config.get("APP_ENV", "")).lower() in {"production", "prod"}
    if not enabled or not production:
        return
    required = (
        "CUSTOMER_RECOVERY_EMAIL_FROM",
        "CUSTOMER_RECOVERY_SMTP_HOST",
        "FRONTEND_URL",
    )
    missing = [name for name in required if not str(config.get(name) or "").strip()]
    if missing:
        raise RuntimeError(
            "Customer recovery email is enabled but required SMTP configuration is missing."
        )
    frontend_url = str(config["FRONTEND_URL"]).strip().lower()
    if not frontend_url.startswith("https://"):
        raise RuntimeError("Customer recovery email requires an HTTPS FRONTEND_URL in Production.")
    if _as_bool(config.get("CUSTOMER_RECOVERY_SMTP_USE_SSL")) and _as_bool(
        config.get("CUSTOMER_RECOVERY_SMTP_USE_STARTTLS")
    ):
        raise RuntimeError("Customer recovery SMTP cannot enable SSL and STARTTLS together.")
    username = str(config.get("CUSTOMER_RECOVERY_SMTP_USERNAME") or "")
    password = str(config.get("CUSTOMER_RECOVERY_SMTP_PASSWORD") or "")
    if bool(username) != bool(password):
        raise RuntimeError("Customer recovery SMTP username and password must be configured together.")


def build_password_reset_url(raw_token: str) -> str:
    frontend_url = str(current_app.config["FRONTEND_URL"]).rstrip("/")
    return f"{frontend_url}/customer/reset-password?{urlencode({'token': raw_token})}"


def send_password_recovery_email(
    recipient: str,
    reset_url: str,
    expires_at: datetime,
) -> str:
    """Submit one password-recovery email without logging recipient or capability."""
    config = current_app.config
    production = str(config.get("APP_ENV", "")).lower() in {"production", "prod"}
    if not production or not _as_bool(config.get("CUSTOMER_RECOVERY_EMAIL_ENABLED")):
        current_app.logger.info("Customer recovery email delivery suppressed by environment policy.")
        return DELIVERY_SUPPRESSED

    try:
        validate_recovery_email_configuration(config)
        message = EmailMessage()
        message["Subject"] = "بازیابی رمز عبور فورواردِر"
        message["From"] = str(config["CUSTOMER_RECOVERY_EMAIL_FROM"])
        message["To"] = recipient
        message.set_content(
            "برای تعیین رمز عبور جدید، پیوند زیر را باز کنید:\n\n"
            f"{reset_url}\n\n"
            f"این پیوند یک‌بارمصرف است و تا {expires_at.isoformat()} معتبر خواهد بود.\n"
            "اگر این درخواست را ثبت نکرده‌اید، این پیام را نادیده بگیرید."
        )

        host = str(config["CUSTOMER_RECOVERY_SMTP_HOST"])
        port = int(config.get("CUSTOMER_RECOVERY_SMTP_PORT", 587))
        timeout = int(config.get("CUSTOMER_RECOVERY_SMTP_TIMEOUT_SECONDS", 10))
        use_ssl = _as_bool(config.get("CUSTOMER_RECOVERY_SMTP_USE_SSL"))
        use_starttls = _as_bool(config.get("CUSTOMER_RECOVERY_SMTP_USE_STARTTLS"))
        username = str(config.get("CUSTOMER_RECOVERY_SMTP_USERNAME") or "")
        password = str(config.get("CUSTOMER_RECOVERY_SMTP_PASSWORD") or "")
        if use_ssl:
            client = smtplib.SMTP_SSL(
                host,
                port,
                timeout=timeout,
                context=ssl.create_default_context(),
            )
        else:
            client = smtplib.SMTP(host, port, timeout=timeout)
        with client:
            client.ehlo()
            if use_starttls:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if username:
                client.login(username, password)
            client.send_message(message)
        current_app.logger.info("Customer recovery email accepted by SMTP adapter.")
        return DELIVERY_SENT
    except Exception as exc:  # provider/network details may contain secrets
        current_app.logger.error(
            "Customer recovery email delivery failed (%s).", type(exc).__name__
        )
        return DELIVERY_FAILED


__all__ = [
    "DELIVERY_FAILED",
    "DELIVERY_SENT",
    "DELIVERY_SUPPRESSED",
    "build_password_reset_url",
    "send_password_recovery_email",
    "validate_recovery_email_configuration",
]
