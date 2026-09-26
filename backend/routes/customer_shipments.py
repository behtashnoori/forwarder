"""Authenticated Customer projection; no public or write alias."""
from flask import Blueprint, g, jsonify, request
from backend.services import customer_shipment_service as service
from backend.services.customer_portal_auth import require_customer
from backend.services.operational_service import OperationalError

customer_shipments_bp = Blueprint("customer_shipments", __name__, url_prefix="/api/customer/shipments")


@customer_shipments_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.vary.add("Cookie")
    return response


@customer_shipments_bp.get("")
@require_customer
def listing():
    try:
        return jsonify(service.authorized_read(g.current_customer, service.listing, request.args.get("page", "1"), request.args.get("q", "")))
    except OperationalError as exc:
        return jsonify({"code": exc.code, "message": exc.message}), exc.status


@customer_shipments_bp.get("/<shipment_id>")
@require_customer
def detail(shipment_id):
    try:
        return jsonify(service.authorized_read(g.current_customer, service.detail, shipment_id, **{
            name: request.args.get(name, "1") for name in ("documents_page", "deliveries_page", "timeline_page")}))
    except OperationalError as exc:
        return jsonify({"code": exc.code, "message": exc.message}), exc.status


@customer_shipments_bp.get("/authorization")
@require_customer
def authorization():
    try:
        return jsonify({"authorization_revision": service.authorization_revision(g.current_customer)})
    except OperationalError as exc:
        return jsonify({"code": exc.code, "message": exc.message}), exc.status
