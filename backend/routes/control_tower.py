"""Authenticated, allowlisted presentation of the governed Control Tower read."""
from flask import Blueprint, jsonify, request

from backend.auth import get_current_user
from backend.extensions import db
from backend.security import require_auth
from backend.services import oip_service
from backend.services.control_tower_read_model import compose_control_tower, ControlTowerCursorInvalid
from backend.services.control_tower_scope import (
    ControlTowerResponsibilityInvariant,
    ControlTowerScopeDenied,
)
from backend.services.control_tower_translation import UNAVAILABLE_MESSAGE
from backend.services.operational_service import OperationalError, organization_for_user

control_tower_bp = Blueprint("control_tower", __name__)


def _reason(reason):
    return {
        "semantic": reason.semantic, "title": reason.title, "explanation": reason.explanation,
        "time": [{"label": value.label, "at": value.at.isoformat()} for value in reason.time],
    }


def _error(code, message, status):
    db.session.rollback()
    return jsonify({"error": {"code": code, "message": message}}), status


@control_tower_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@control_tower_bp.get("/api/control-tower/shipments")
@require_auth
def shipments():
    try:
        actor = get_current_user()
        page_size = int(request.args.get("page_size", "25"))
        result = compose_control_tower(
            actor, page_size=page_size, cursor=request.args.get("cursor"),
            attention=request.args.get("attention"),
            search=request.args.get("search"),
        )
        health = oip_service.projection_health_for_organization(
            organization_for_user(int(actor["id"]))
        )
    except ControlTowerScopeDenied:
        return _error("FORBIDDEN_OPERATION", "دسترسی به این صفحه امکان‌پذیر نیست.", 403)
    except ControlTowerCursorInvalid:
        return _error("INVALID_CURSOR", "دریافت ادامه موارد امکان‌پذیر نیست. دوباره تلاش کنید.", 400)
    except ValueError:
        return _error("VALIDATION_ERROR", "درخواست معتبر نیست.", 400)
    except ControlTowerResponsibilityInvariant:
        return _error("EVALUATION_UNAVAILABLE", UNAVAILABLE_MESSAGE, 503)
    except OperationalError:
        return _error("EVALUATION_UNAVAILABLE", UNAVAILABLE_MESSAGE, 503)
    if result.state != "complete":
        return _error("EVALUATION_UNAVAILABLE", UNAVAILABLE_MESSAGE, 503)
    empty_message = result.empty_message
    if result.summary.total == 0 and health["health_state"] != "FRESH":
        empty_message = "در داده‌های آخرین ارزیابی هشدار فعالی دیده نمی‌شود؛ ارزیابی Attention به‌روز نیست و این نتیجه اثبات سلامت عملیات نیست."
    return jsonify({"data": {
        "evaluatedAt": result.evaluated_at.isoformat(), "state": result.state,
        "notice": result.notice, "emptyMessage": empty_message,
        "attentionEvaluation": {
            "state": health["health_state"], "trustworthy": health["trustworthy"],
            "checkedAt": health["checked_at"],
            "lastAttemptAt": health["last_evaluation_attempt_at"],
            "lastSuccessAt": health["last_evaluation_success_at"],
            "nextEvaluationDueAt": health["next_evaluation_due_at"],
            "reasonCode": health["reason_code"], "reason": health["reason"],
            "lastRun": health["last_run"],
        },
        "summary": {
            "total": result.summary.total,
            "attentionCounts": {
                "urgent": result.summary.attention_counts["urgent"],
                "followUp": result.summary.attention_counts["follow_up"],
                "review": result.summary.attention_counts["review"],
            },
        },
        "page": {
            "limit": result.page.limit,
            "offset": result.page.offset,
            "returned": result.page.returned,
            "hasMore": result.page.has_more,
            "nextCursor": result.page.next_cursor,
        },
        "items": [{
            "key": item.shipment_reference, "shipmentReference": item.shipment_reference,
            "routeLabel": item.route_label, "transportLabel": item.transport_label,
            "actualRouteModes": list(item.actual_route_modes),
            "operationalStatus": item.operational_status,
            "source": item.source,
            "requestTransport": item.request_transport,
            "progress": item.progress,
            "workSummary": item.work_summary,
            "attention": item.attention, "attentionLabel": item.attention_label,
            "ownerName": item.owner_name, "primaryReason": _reason(item.primary_reason),
            "additionalReasons": [_reason(reason) for reason in item.additional_reasons],
            "destination": item.destination,
        } for item in result.items],
    }})
