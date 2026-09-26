"""Explicit idempotent ETA materialization and pure historical reads."""
from flask import Blueprint, g, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import eta_service as service, customer_shipment_service as customers
from backend.services.customer_portal_auth import require_customer
from backend.services.operational_service import OperationalError

eta_bp = Blueprint("eta", __name__)


@eta_bp.after_request
def no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.vary.add("Cookie")
    return response


def _run(shipment_id, cargo_id, *, customer=False, ensure=False):
    user = None if customer else get_current_user()
    account_id = g.current_customer.id if customer else None
    if ensure and (request.get_json(silent=True) not in (None, {})):
        return jsonify({"code": "ETA_INPUT_FORBIDDEN", "message": "مبنای برآورد از اطلاعات ثبت‌شده خوانده می‌شود."}), 422
    # Authentication has only read state. This endpoint owns its dedicated unit
    # of work; discard that read transaction before selecting isolation.
    db.session.remove()
    for attempt in range(3):
        try:
            if ensure and db.engine.dialect.name == "postgresql":
                db.session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            if customer:
                from backend.models import CustomerGamification
                account = db.session.get(CustomerGamification, account_id, populate_existing=True)
                if account is None:
                    raise OperationalError("SESSION_REVOKED", "نشست پایان یافته است.", 401)
                revision = customers.authorization_revision(account)
            else:
                account, revision = None, None
            kwargs = {"user": user, "account": account}
            if ensure:
                row = service.ensure_current_eta(str(shipment_id), str(cargo_id), **kwargs)
                value = service.project(row, customer=customer)
                expected_fingerprint = row.source_fingerprint
                db.session.commit()
                # A fresh transaction checks authorization and source identity
                # after commit. Never return a snapshot known to be stale.
                db.session.remove()
                if customer:
                    account = db.session.get(CustomerGamification, account_id, populate_existing=True)
                    if account is None or customers.authorization_revision(account) != revision:
                        raise OperationalError("CUSTOMER_SCOPE_CHANGED", "دسترسی تغییر کرده است؛ دوباره بخوانید.", 409)
                    kwargs["account"] = account
                shipment, cargo = service._scope(str(shipment_id), str(cargo_id), **kwargs)
                _, basis, _, _ = service.calculate(shipment, cargo, customer=customer)
                if service._fingerprint(basis) != expected_fingerprint:
                    db.session.remove()
                    if attempt < 2:
                        continue
                    raise OperationalError("ETA_SOURCE_CHANGED", "اطلاعات حمل تغییر کرده است؛ دوباره بخوانید.", 409)
            else:
                value = service.history(str(shipment_id), str(cargo_id), page=request.args.get("page", 1), **kwargs)
            if customer:
                if customers.authorization_revision(account) != revision:
                    raise OperationalError("CUSTOMER_SCOPE_CHANGED", "دسترسی تغییر کرده است؛ دوباره بخوانید.", 409)
                value["authorization_revision"] = revision
            return jsonify(value)
        except OperationalError as exc:
            db.session.rollback()
            return jsonify({"code": exc.code, "message": exc.message}), exc.status
        except DBAPIError as exc:
            db.session.rollback()
            code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
            if code in {"40001", "40P01", "23505"} and attempt < 2:
                db.session.remove()
                continue
            if code in {"40001", "40P01", "23505"}:
                return jsonify({"code": "ETA_SOURCE_CHANGED", "message": "اطلاعات هم‌زمان تغییر کرد؛ دوباره بخوانید."}), 409
            raise


@eta_bp.post("/api/operational-shipments/<uuid:shipment_id>/cargo/<uuid:cargo_id>/eta/ensure")
@require_auth
def ensure_internal(shipment_id, cargo_id):
    return _run(shipment_id, cargo_id, ensure=True)


@eta_bp.get("/api/operational-shipments/<uuid:shipment_id>/cargo/<uuid:cargo_id>/eta/history")
@require_auth
def history_internal(shipment_id, cargo_id):
    return _run(shipment_id, cargo_id)


@eta_bp.post("/api/customer/shipments/<uuid:shipment_id>/cargo/<uuid:cargo_id>/eta/ensure")
@require_customer
def ensure_customer(shipment_id, cargo_id):
    return _run(shipment_id, cargo_id, customer=True, ensure=True)


@eta_bp.get("/api/customer/shipments/<uuid:shipment_id>/cargo/<uuid:cargo_id>/eta/history")
@require_customer
def history_customer(shipment_id, cargo_id):
    return _run(shipment_id, cargo_id, customer=True)
