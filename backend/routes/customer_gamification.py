"""Customer Portal and tenant-scoped portal-account support routes."""
from __future__ import annotations
from typing import Any
from datetime import datetime, timedelta
from flask import Blueprint, current_app, g, jsonify, request
from backend.services import customer_gamification_service
from backend.services.admin_authorization_service import require_organization_admin_context
from backend.services.customer_account_lifecycle_service import (
    change_password, consume_recovery_token, issue_recovery_token, queue_admin_recovery_request,
    request_password_recovery, set_account_enabled,
)
from backend.services.customer_portal_auth import (
    CustomerPortalAuthError, clear_customer_session, customer_summary,
    error_payload as auth_error_payload, login_customer, register_customer as register_portal_customer,
    require_customer, require_customer_csrf, session_payload,
)
from backend.services.customer_portal_service import (
    CustomerPortalError, customer_request_detail, list_customer_requests,
    list_tenant_accounts, respond_to_quote, tenant_account_or_404,
)
from backend.services.organization_hostname_service import resolve_organization_for_host

customer_gamification_bp = Blueprint("customer_gamification", __name__, url_prefix="/api/customer")
customer_portal_admin_bp = Blueprint("customer_portal_admin", __name__, url_prefix="/api/admin/customer-portal-accounts")

def _json() -> dict[str, Any]: return request.get_json(silent=True) or {}
def _portal_error(exc): return jsonify({"code": exc.code, "message": exc.message}), exc.status_code

@customer_gamification_bp.post("/register")
def register_customer():
    data = _json()
    if "password" not in data:
        payload, status = customer_gamification_service.register_customer(data)
        return jsonify(payload), status
    try:
        organization = resolve_organization_for_host(request.host)
        if organization is None:
            raise CustomerPortalAuthError(
                "Customer account signup is unavailable for this hostname.",
                409,
                "ORGANIZATION_CONTEXT_REQUIRED",
            )
        return jsonify(register_portal_customer(data, organization_id=organization.id)), 201
    except CustomerPortalAuthError as exc:
        body, status = auth_error_payload(exc); return jsonify(body), status

@customer_gamification_bp.post("/login")
def login():
    try: return jsonify(login_customer(_json())), 200
    except CustomerPortalAuthError as exc:
        body, status = auth_error_payload(exc); return jsonify(body), status

@customer_gamification_bp.get("/session")
def get_session(): return jsonify(session_payload()), 200

@customer_gamification_bp.post("/logout")
@require_customer_csrf
def logout():
    clear_customer_session(); return jsonify({"authenticated": False}), 200

@customer_gamification_bp.get("/verify-email")
def verify_email():
    payload, status = customer_gamification_service.verify_customer_email(request.args.get("token"))
    return jsonify(payload), status

@customer_gamification_bp.get("/profile")
@require_customer
def profile(): return jsonify({"customer": customer_summary(g.current_customer)}), 200

@customer_gamification_bp.get("/profile/<int:customer_id>")
@require_customer
def legacy_profile(customer_id):
    if customer_id != g.current_customer.id:
        return jsonify({"message": "مشتری یافت نشد"}), 404
    payload = customer_gamification_service.get_customer_profile_payload(customer_id)
    return (jsonify(payload), 200) if payload else (jsonify({"message": "مشتری یافت نشد"}), 404)

@customer_gamification_bp.get("/requests")
@require_customer
def requests_list():
    return jsonify(list_customer_requests(g.current_customer.id, request.args.get("page", 1, type=int), request.args.get("per_page", 20, type=int))), 200

@customer_gamification_bp.get("/requests/<request_public_id>")
@require_customer
def request_detail(request_public_id):
    try: return jsonify(customer_request_detail(g.current_customer.id, request_public_id)), 200
    except CustomerPortalError as exc: return _portal_error(exc)

@customer_gamification_bp.post("/requests/<request_public_id>/quotes/<quote_public_id>/response")
@require_customer_csrf
def quote_response(request_public_id, quote_public_id):
    try: return jsonify(respond_to_quote(g.current_customer.id, request_public_id, quote_public_id, _json(), request.remote_addr)), 200
    except CustomerPortalError as exc: return _portal_error(exc)

@customer_gamification_bp.post("/quote-response/<tracking_code>")
@customer_gamification_bp.post("/quotes/<quote_public_id>/response")
def removed_public_quote_writer(**_kwargs):
    return jsonify({"code": "QUOTE_NOT_FOUND", "message": "Not found"}), 404

@customer_gamification_bp.get("/workflow/<int:customer_id>")
@require_customer
def legacy_workflow(customer_id):
    if customer_id != g.current_customer.id:
        return jsonify({"message": "درخواست یافت نشد یا به این مشتری تعلق ندارد"}), 404
    request_id_arg = request.args.get("request_id")
    if not request_id_arg:
        return jsonify({"message": "شناسه درخواست الزامی است"}), 400
    try:
        request_id = int(request_id_arg)
    except (TypeError, ValueError):
        return jsonify({"message": "شناسه درخواست نامعتبر است"}), 400
    payload = customer_gamification_service.get_customer_workflow_payload(customer_id, request_id)
    return (jsonify(payload), 200) if payload else (jsonify({"message": "درخواست یافت نشد یا به این مشتری تعلق ندارد"}), 404)

@customer_gamification_bp.post("/complete-step")
@require_customer_csrf
def complete_workflow_step():
    data = _json(); data["customer_id"] = g.current_customer.id
    payload, status = customer_gamification_service.complete_customer_workflow_step(data)
    return jsonify(payload), status

@customer_gamification_bp.get("/leaderboard")
def leaderboard(): return jsonify(customer_gamification_service.list_leaderboard_payload()), 200

@customer_gamification_bp.post("/password/change")
@require_customer_csrf
def password_change():
    data = _json()
    try:
        change_password(g.current_customer, data.get("current_password"), data.get("new_password")); clear_customer_session()
        return jsonify({"authenticated": False, "code": "PASSWORD_CHANGED"}), 200
    except CustomerPortalAuthError as exc:
        body, status = auth_error_payload(exc); return jsonify(body), status

@customer_gamification_bp.post("/password/forgot")
def password_forgot():
    request_password_recovery(_json().get("email"))
    return jsonify({"code": "RECOVERY_REQUEST_ACCEPTED", "message": "If the account is eligible, recovery will be initiated."}), 202

def _consume_token(purpose):
    data = _json()
    try:
        consume_recovery_token(data.get("token"), data.get("new_password"), purpose); clear_customer_session()
        return jsonify({"authenticated": False, "code": "PASSWORD_RESET"}), 200
    except CustomerPortalAuthError as exc:
        body, status = auth_error_payload(exc); return jsonify(body), status

@customer_gamification_bp.post("/password/reset")
def password_reset(): return _consume_token("RESET")

@customer_gamification_bp.post("/enrollment/complete")
def enrollment_complete(): return _consume_token("ENROLLMENT")

@customer_portal_admin_bp.get("")
@require_organization_admin_context(allow_platform=False)
def admin_list_accounts():
    return jsonify(list_tenant_accounts(int(g.organization_context.organization_id), request.args.get("q", ""), request.args.get("status"), request.args.get("page", 1, type=int), request.args.get("per_page", 20, type=int))), 200

def _admin_customer(public_id): return tenant_account_or_404(int(g.organization_context.organization_id), public_id)

@customer_portal_admin_bp.post("/<public_id>/disable")
@require_organization_admin_context(allow_platform=False)
def admin_disable_account(public_id):
    try:
        customer = _admin_customer(public_id); set_account_enabled(customer, False, int(g.current_user_id))
        return jsonify({"customer": customer_summary(customer)}), 200
    except CustomerPortalError as exc: return _portal_error(exc)

@customer_portal_admin_bp.post("/<public_id>/enable")
@require_organization_admin_context(allow_platform=False)
def admin_enable_account(public_id):
    try:
        customer = _admin_customer(public_id); set_account_enabled(customer, True, int(g.current_user_id))
        return jsonify({"customer": customer_summary(customer)}), 200
    except CustomerPortalError as exc: return _portal_error(exc)

@customer_portal_admin_bp.post("/<public_id>/status")
@require_organization_admin_context(allow_platform=False)
def admin_set_account_status(public_id):
    try:
        customer = _admin_customer(public_id); status = _json().get("status")
        if status not in {"ACTIVE", "DISABLED"}: return jsonify({"code": "INVALID_ACCOUNT_STATUS", "message": "Status must be ACTIVE or DISABLED."}), 400
        set_account_enabled(customer, status == "ACTIVE", int(g.current_user_id))
        return jsonify({"account": customer_summary(customer)}), 200
    except CustomerPortalError as exc: return _portal_error(exc)

def _issue_admin_capability(public_id, purpose):
    customer = _admin_customer(public_id)
    if customer.account_status != "ACTIVE":
        return jsonify({"code": "ACCOUNT_DISABLED", "message": "Account is disabled."}), 409
    if purpose == "ENROLLMENT" and customer.password_hash:
        return jsonify({"code": "ACCOUNT_ALREADY_ENROLLED", "message": "Account enrollment is already complete."}), 409
    if purpose == "RESET" and not customer.password_hash:
        return jsonify({"code": "ACCOUNT_ENROLLMENT_REQUIRED", "message": "Account enrollment must be completed first."}), 409
    row = queue_admin_recovery_request(customer, int(g.current_user_id), purpose)
    try:
        raw_token = issue_recovery_token(
            customer, purpose, created_by_user_id=int(g.current_user_id), recovery_request=row
        )
    except CustomerPortalAuthError as exc:
        body, status = auth_error_payload(exc); return jsonify(body), status
    lifetime = int(current_app.config.get("CUSTOMER_RECOVERY_TOKEN_LIFETIME_SECONDS", 1800))
    route = "/customer/reset-password" if purpose == "RESET" else "/customer/enroll"
    return jsonify({
        "message": "One-time customer capability issued.",
        "purpose": purpose,
        "path": f"{route}?token={raw_token}",
        "expires_at": (datetime.utcnow() + timedelta(seconds=lifetime)).isoformat(),
    }), 201

@customer_portal_admin_bp.post("/<public_id>/recovery")
@require_organization_admin_context(allow_platform=False)
def admin_recovery(public_id):
    try: return _issue_admin_capability(public_id, "RESET")
    except CustomerPortalError as exc: return _portal_error(exc)

@customer_portal_admin_bp.post("/<public_id>/enrollment")
@require_organization_admin_context(allow_platform=False)
def admin_enrollment(public_id):
    try: return _issue_admin_capability(public_id, "ENROLLMENT")
    except CustomerPortalError as exc: return _portal_error(exc)

@customer_portal_admin_bp.post("/<public_id>/recovery-requests")
@require_organization_admin_context(allow_platform=False)
def admin_initiate_recovery(public_id):
    try:
        customer = _admin_customer(public_id); purpose = _json().get("purpose")
        if purpose not in {"RESET", "ENROLLMENT"}: return jsonify({"code": "INVALID_RECOVERY_PURPOSE", "message": "Purpose must be RESET or ENROLLMENT."}), 400
        if customer.account_status != "ACTIVE": return jsonify({"code": "ACCOUNT_DISABLED", "message": "Account is disabled."}), 409
        return _issue_admin_capability(public_id, purpose)
    except CustomerPortalError as exc: return _portal_error(exc)

__all__ = ["customer_gamification_bp", "customer_portal_admin_bp"]
