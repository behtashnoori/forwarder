"""Service helpers for expert quote workflows."""
from datetime import date, datetime
from typing import Any, Optional

from backend.extensions import db
from backend.models import (
    ExpertConsoleLog,
    ExpertConsoleNotification,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.services.ownership_service import OwnershipContractError, require_tenant_resource


class QuoteServiceError(Exception):
    """Base service exception that maps to the current quote API error payload."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QuoteValidationError(QuoteServiceError):
    """Raised for current quote validation failures."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class QuoteNotFoundError(QuoteServiceError):
    """Raised when the target request or expert is missing."""


class QuoteAccessError(QuoteServiceError):
    """Raised when the current user cannot access the quote target request."""


def manage_quote_capability(request_id, quote_public_id, user, operation):
    from backend.census_context import census_unit_of_work
    from backend.services.quote_response_authorization import manage_grant, ScopeChanged
    from backend.services.quote_capability_crypto import CapabilityDenied
    if db.session.new or db.session.dirty or db.session.deleted:
        raise QuoteAccessError('QUOTE_COMMAND_REQUIRES_CLEAN_UNIT_OF_WORK', 409)
    for attempt in range(3):
        db.session.rollback()
        try:
            with census_unit_of_work(db.session):
                result = manage_grant(request_id, quote_public_id, user, operation)
                db.session.commit()
                return result
        except ScopeChanged:
            db.session.rollback()
            if attempt == 2:
                raise QuoteAccessError('SCOPE_CHANGED_RETRY', 409) from None
        except CapabilityDenied as exc:
            db.session.rollback()
            if str(exc) == 'TARGET_UNAVAILABLE':
                raise QuoteNotFoundError('درخواست یافت نشد', 404) from None
            raise QuoteAccessError(str(exc), 403) from None
        except Exception:
            db.session.rollback()
            raise


def create_quote_for_request(
    request_id: int, payload: dict[str, Any], user: dict[str, Any],
    remote_addr: Optional[str] = None,
) -> dict[str, Any]:
    """Governed publication; caller boundary owns one atomic commit."""
    from backend.services.governed_quote_service import publish, QuoteConflict
    from backend.services.quote_response_authorization import ScopeChanged
    from backend.services.quote_capability_crypto import CapabilityDenied
    from backend.census_context import census_unit_of_work
    if db.session.new or db.session.dirty or db.session.deleted:
        raise QuoteAccessError("QUOTE_COMMAND_REQUIRES_CLEAN_UNIT_OF_WORK", 409)
    for attempt in range(3):
        db.session.rollback()
        try:
            with census_unit_of_work(db.session):
                result = publish(request_id, payload, user)
                db.session.commit()
                return result
        except ScopeChanged:
            db.session.rollback()
            if attempt == 2:
                raise QuoteAccessError("SCOPE_CHANGED_RETRY", 409) from None
        except QuoteConflict as exc:
            db.session.rollback()
            raise QuoteAccessError(str(exc), 409) from None
        except CapabilityDenied as exc:
            db.session.rollback()
            if str(exc) == 'TARGET_UNAVAILABLE':
                raise QuoteNotFoundError('درخواست یافت نشد', 404) from None
            raise QuoteAccessError(str(exc), 403) from None
        except ValueError as exc:
            db.session.rollback()
            reason = str(exc)
            if reason == "QUOTATION_TIMEZONE_NOT_CONFIGURED":
                reason = "منطقه زمانی اعتبار پیشنهاد تنظیم نشده است؛ از مدیر سازمان بخواهید آن را تنظیم کند."
            raise QuoteValidationError(reason) from None
        except Exception:
            db.session.rollback()
            raise


def get_latest_quote_for_request(request_id: int, user: dict[str, Any]) -> ExpertQuote | None:
    """Return latest quote for a request, preserving current not-found/access behavior."""
    req = get_quote_target_request_or_none(request_id)
    if not req:
        raise QuoteNotFoundError("درخواست یافت نشد", 404)
    if not can_access_quote_request(req, user):
        raise QuoteAccessError("شما به این درخواست دسترسی ندارید", 403)

    from backend.services.governed_quote_service import effective_quote_for_root
    return effective_quote_for_root(request_id)


def build_latest_quote_response_payload(quote: ExpertQuote | None) -> dict[str, Any]:
    """Build the current GET latest quote response payload."""
    return {"quote": build_quote_payload(quote, include_created_by=True, include_delivery_readiness=True) if quote else None}


def build_quote_payload(quote: ExpertQuote, include_created_by: bool = False, include_delivery_readiness: bool = False) -> dict[str, Any]:
    from backend.services.governed_quote_service import quote_projection
    payload = quote_projection(quote)
    payload["created_at"] = (quote.published_at.isoformat() if quote.published_at else quote.created_at.isoformat())
    payload["responded_at"] = payload.get("response_received_at") or (quote.responded_at.isoformat() if quote.responded_at else None)
    if include_created_by:
        payload["created_by"] = quote.created_by_expert.full_name if quote.created_by_expert else None
    if include_delivery_readiness and quote.money_contract == 'quote-major.v1':
        from backend.services.quote_response_authorization import quote_readiness_metadata
        payload['delivery_readiness']=quote_readiness_metadata(quote)
    return payload


def normalize_quote_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize quote payload while preserving current tolerant parsing."""
    amount = payload.get("amount")
    currency = (payload.get("currency") or "IRR").strip() or "IRR"
    note = (payload.get("note") or "").strip() or None
    valid_until = payload.get("valid_until")

    if amount is None:
        raise QuoteValidationError("مبلغ الزامی است")
    # Quote amounts are canonically integral in the existing API/DB contract.
    # Reject fractional values instead of truncating them with int().
    if isinstance(amount, bool) or (isinstance(amount, float) and not amount.is_integer()):
        raise QuoteValidationError("مبلغ باید عدد صحیح باشد")
    try:
        amount_int = int(amount)
    except (TypeError, ValueError):
        raise QuoteValidationError("مبلغ باید عدد باشد") from None
    if isinstance(amount, str) and not amount.strip().lstrip("+-").isdigit():
        raise QuoteValidationError("مبلغ باید عدد صحیح باشد")
    if amount_int < 0:
        raise QuoteValidationError("مبلغ نامعتبر است")

    valid_until_date = None
    if valid_until:
        try:
            valid_until_date = date.fromisoformat(valid_until.replace("Z", "").split("T")[0])
        except Exception:
            pass

    return {
        "amount": amount_int,
        "currency": currency,
        "note": note,
        "valid_until": valid_until_date,
    }


def get_quote_target_request_or_none(request_id: int) -> ShipmentRequest | None:
    """Return the target shipment request for quote operations, or None."""
    return db.session.get(ShipmentRequest, request_id)


def can_access_quote_request(req: ShipmentRequest, user: dict[str, Any] | None) -> bool:
    from backend.services.assigned_work_authorization import authorize_work_action
    try:
        require_tenant_resource(req)
        return authorize_work_action(user or {}, req, 'request.read').allowed
    except (ValueError, TypeError):
        return False
