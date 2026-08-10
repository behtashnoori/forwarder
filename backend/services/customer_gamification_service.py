"""Service helpers for customer gamification endpoints."""
from __future__ import annotations

import os
import secrets
from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import CustomerGamification, CustomerWorkflowStep, ExpertConsoleLog, ExpertQuote, ShipmentRequest
from backend.routes.public_tracking import _workflow_steps_simple_4
from backend.services.legacy_datetime import serialize_legacy_utc_datetime


def generate_customer_verification_token() -> str:
    """Generate a secure customer verification token."""
    return secrets.token_urlsafe(32)


def send_registration_verification_email(
    email: str,
    token: str,
    customer_name: str | None = None,
) -> bool:
    """Send the current customer registration verification email side effect."""
    try:
        frontend_url = (os.environ.get("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
        verification_url = f"{frontend_url}/verify-email?token={token}"

        current_app.logger.info(f"Verification email would be sent to {email}")
        current_app.logger.info(f"Verification URL: {verification_url}")

        return True
    except Exception as e:
        current_app.logger.error(f"Error sending verification email: {e}")
        return False


def normalize_registration_payload(payload: dict[str, Any]) -> dict[str, str]:
    """Normalize the current registration input fields."""
    return {
        "email": payload.get("email", "").strip().lower(),
        "phone": payload.get("phone", "").strip(),
        "first_name": payload.get("first_name", "").strip(),
        "last_name": payload.get("last_name", "").strip(),
    }


def validate_registration_payload(data: dict[str, str]) -> tuple[dict[str, str], int] | None:
    """Return the current registration validation error payload, if any."""
    email = data["email"]
    phone = data["phone"]

    if not email or not phone:
        return {"message": "ایمیل و شماره تماس الزامی است"}, 400

    if "@" not in email or "." not in email:
        return {"message": "فرمت ایمیل نامعتبر است"}, 400

    if not phone.startswith("09") or len(phone) != 11 or not phone.isdigit():
        return {"message": "شماره تماس نامعتبر است"}, 400

    return None


def create_customer_registration_record(data: dict[str, str]) -> CustomerGamification:
    """Create and flush the current customer registration row."""
    verification_token = generate_customer_verification_token()
    verification_expires = datetime.utcnow() + timedelta(hours=24)

    customer = CustomerGamification(
        email=data["email"],
        phone=data["phone"],
        first_name=data["first_name"] or None,
        last_name=data["last_name"] or None,
        email_verification_token=verification_token,
        verification_expires_at=verification_expires,
    )

    db.session.add(customer)
    db.session.flush()
    return customer


def build_duplicate_registration_response_payload(customer: CustomerGamification) -> dict[str, Any]:
    """Build the current duplicate registration response payload."""
    return {
        "message": "این ایمیل قبلاً ثبت شده است",
        "customer_id": customer.id,
        "is_verified": customer.is_email_verified,
    }


def build_registration_response_payload(
    customer: CustomerGamification,
    email_sent: bool,
) -> dict[str, Any]:
    """Build the current successful registration response payload."""
    return {
        "message": "ثبت‌نام با موفقیت انجام شد. لطفاً ایمیل خود را تایید کنید.",
        "customer_id": customer.id,
        "email_sent": email_sent,
    }


def register_customer(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Register a customer with the current API behavior and transaction boundaries."""
    data = normalize_registration_payload(payload)
    validation_error = validate_registration_payload(data)
    if validation_error:
        return validation_error

    try:
        existing_customer = (
            db.session.query(CustomerGamification)
            .filter(CustomerGamification.email == data["email"])
            .first()
        )

        if existing_customer:
            return build_duplicate_registration_response_payload(existing_customer), 200

        customer = create_customer_registration_record(data)

        customer_name = (
            f"{data['first_name']} {data['last_name']}".strip()
            if data["first_name"] or data["last_name"]
            else None
        )
        email_sent = send_registration_verification_email(
            data["email"],
            customer.email_verification_token,
            customer_name,
        )

        if not email_sent:
            current_app.logger.warning(f"Failed to send verification email to {data['email']}")

        db.session.commit()

        return build_registration_response_payload(customer, email_sent), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in customer registration: {e}")
        return {"message": "خطا در ثبت‌نام"}, 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in customer registration: {e}")
        return {"message": "خطای داخلی سرور"}, 500


def get_customer_by_verification_token(token: str) -> CustomerGamification | None:
    """Return the currently valid customer email verification token match."""
    return (
        db.session.query(CustomerGamification)
        .filter(
            CustomerGamification.email_verification_token == token,
            CustomerGamification.verification_expires_at > datetime.utcnow(),
        )
        .first()
    )


def apply_customer_email_verification(customer: CustomerGamification) -> None:
    """Apply the current verified-state and token-clearing mutation."""
    customer.is_email_verified = True
    customer.email_verification_token = None
    customer.verification_expires_at = None


def apply_verification_points_and_workflow_effects(customer: CustomerGamification) -> None:
    """Apply the current email-verification points and workflow step side effects."""
    customer.update_loyalty_points(10)

    workflow_step = CustomerWorkflowStep(
        customer_id=customer.id,
        shipment_request_id=0,
        step_name="email_verified",
        step_order=1,
        is_completed=True,
        completed_at=datetime.utcnow(),
        points_earned=10,
    )
    db.session.add(workflow_step)


def build_email_verification_success_payload(customer: CustomerGamification) -> dict[str, Any]:
    """Build the current email verification success response payload."""
    return {
        "message": "ایمیل شما با موفقیت تایید شد! ۱۰ امتیاز دریافت کردید.",
        "customer_id": customer.id,
        "loyalty_points": customer.loyalty_points,
        "customer_level": customer.customer_level,
    }


def verify_customer_email(token: str | None) -> tuple[dict[str, Any], int]:
    """Verify a customer email with the current API behavior and transaction boundaries."""
    if not token:
        return {"message": "توکن تایید الزامی است"}, 400

    try:
        customer = get_customer_by_verification_token(token)

        if not customer:
            return {"message": "توکن تایید نامعتبر یا منقضی شده است"}, 400

        apply_customer_email_verification(customer)
        apply_verification_points_and_workflow_effects(customer)

        db.session.commit()

        return build_email_verification_success_payload(customer), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in email verification: {e}")
        return {"message": "خطا در تایید ایمیل"}, 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in email verification: {e}")
        return {"message": "خطای داخلی سرور"}, 500


def normalize_complete_step_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the current complete-step payload without changing value semantics."""
    return {
        "customer_id": payload.get("customer_id"),
        "request_id": payload.get("request_id"),
        "step_name": payload.get("step_name"),
    }


def validate_complete_step_payload(data: dict[str, Any]) -> tuple[dict[str, str], int] | None:
    """Return the current complete-step validation error payload, if any."""
    if not all([data["customer_id"], data["request_id"], data["step_name"]]):
        return {"message": "تمام فیلدها الزامی است"}, 400
    return None


def get_existing_customer_workflow_step(
    customer_id: Any,
    request_id: Any,
    step_name: Any,
) -> CustomerWorkflowStep | None:
    """Return an existing workflow step using the current lookup behavior."""
    return (
        db.session.query(CustomerWorkflowStep)
        .filter(
            CustomerWorkflowStep.customer_id == customer_id,
            CustomerWorkflowStep.shipment_request_id == request_id,
            CustomerWorkflowStep.step_name == step_name,
        )
        .first()
    )


def get_complete_step_points(step_name: Any) -> int:
    """Return the current points value for a workflow step name."""
    step_points = {
        "email_verified": 10,
        "request_submitted": 20,
        "expert_assigned": 15,
        "expert_contacted": 25,
        "quote_provided": 30,
        "contract_signed": 50,
        "shipment_picked_up": 40,
        "shipment_delivered": 100,
    }
    return step_points.get(step_name, 0)


def get_complete_step_order(step_name: Any) -> int:
    """Return the current step order for a workflow step name."""
    step_order = {
        "email_verified": 1,
        "request_submitted": 2,
        "expert_assigned": 3,
        "expert_contacted": 4,
        "quote_provided": 5,
        "contract_signed": 6,
        "shipment_picked_up": 7,
        "shipment_delivered": 8,
    }
    return step_order.get(step_name, 0)


def create_or_update_completed_workflow_step(
    data: dict[str, Any],
    existing_step: CustomerWorkflowStep | None,
    points: int,
) -> CustomerWorkflowStep:
    """Create or update a workflow step using the current complete-step behavior."""
    if existing_step:
        existing_step.is_completed = True
        existing_step.completed_at = datetime.utcnow()
        existing_step.points_earned = points
        return existing_step

    new_step = CustomerWorkflowStep(
        customer_id=data["customer_id"],
        shipment_request_id=data["request_id"],
        step_name=data["step_name"],
        step_order=get_complete_step_order(data["step_name"]),
        is_completed=True,
        completed_at=datetime.utcnow(),
        points_earned=points,
    )
    db.session.add(new_step)
    return new_step


def get_customer_for_step_completion(customer_id: Any) -> CustomerGamification | None:
    """Return the customer for complete-step point mutation, preserving missing behavior."""
    return (
        db.session.query(CustomerGamification)
        .filter(CustomerGamification.id == customer_id)
        .first()
    )


def apply_complete_step_points(
    customer: CustomerGamification | None,
    points: int,
) -> None:
    """Apply points only when the customer currently exists."""
    if customer:
        customer.update_loyalty_points(points)


def build_complete_step_response_payload(
    step_name: Any,
    points: int,
    customer: CustomerGamification | None,
) -> dict[str, Any]:
    """Build the current complete-step success response payload."""
    return {
        "message": f"مرحله {step_name} با موفقیت تکمیل شد! {points} امتیاز دریافت کردید.",
        "points_earned": points,
        "total_points": customer.loyalty_points if customer else 0,
        "customer_level": customer.customer_level if customer else "bronze",
    }


def complete_customer_workflow_step(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Complete a customer workflow step with current API behavior and transactions."""
    data = normalize_complete_step_payload(payload)
    validation_error = validate_complete_step_payload(data)
    if validation_error:
        return validation_error

    try:
        existing_step = get_existing_customer_workflow_step(
            data["customer_id"],
            data["request_id"],
            data["step_name"],
        )

        if existing_step and existing_step.is_completed:
            return {"message": "این مرحله قبلاً تکمیل شده است"}, 200

        points = get_complete_step_points(data["step_name"])
        create_or_update_completed_workflow_step(data, existing_step, points)

        customer = get_customer_for_step_completion(data["customer_id"])
        apply_complete_step_points(customer, points)

        db.session.commit()

        return build_complete_step_response_payload(data["step_name"], points, customer), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error completing workflow step: {e}")
        return {"message": "خطا در تکمیل مرحله"}, 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing workflow step: {e}")
        return {"message": "خطای داخلی سرور"}, 500


def get_customer_profile_or_none(customer_id: int) -> CustomerGamification | None:
    """Return the customer profile row for the public profile endpoint."""
    return (
        db.session.query(CustomerGamification)
        .filter(CustomerGamification.id == customer_id)
        .first()
    )


def build_customer_profile_payload(customer: CustomerGamification) -> dict[str, Any]:
    """Build the current customer profile response shape."""
    recent_steps = (
        db.session.query(CustomerWorkflowStep)
        .filter(CustomerWorkflowStep.customer_id == customer.id)
        .order_by(CustomerWorkflowStep.created_at.desc())
        .limit(10)
        .all()
    )

    recent_requests = (
        db.session.query(ShipmentRequest)
        .filter(ShipmentRequest.gamification_customer_id == customer.id)
        .order_by(ShipmentRequest.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "customer": {
            "id": customer.id,
            "email": customer.email,
            "phone": customer.phone,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "is_email_verified": customer.is_email_verified,
            "total_requests": customer.total_requests,
            "completed_requests": customer.completed_requests,
            "loyalty_points": customer.loyalty_points,
            "customer_level": customer.customer_level,
            "created_at": customer.created_at.isoformat(),
        },
        "recent_steps": [
            {
                "step_name": step.step_name,
                "step_order": step.step_order,
                "is_completed": step.is_completed,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "points_earned": step.points_earned,
                "created_at": step.created_at.isoformat(),
            }
            for step in recent_steps
        ],
        "recent_requests": [
            {
                "id": req.id,
                "shipping_type": req.shipping_type,
                "status": req.status,
                "created_at": serialize_legacy_utc_datetime(req.created_at),
                "assigned_expert": {
                    "id": req.assigned_expert.id,
                    "full_name": req.assigned_expert.full_name,
                    "phone": req.assigned_expert.phone,
                } if req.assigned_expert else None,
            }
            for req in recent_requests
        ],
    }


def get_customer_profile_payload(customer_id: int) -> dict[str, Any] | None:
    """Return the public profile payload, or None when the customer is missing."""
    customer = get_customer_profile_or_none(customer_id)
    if customer is None:
        return None

    return build_customer_profile_payload(customer)


def get_customer_workflow_or_none(customer_id: int, request_id: int) -> ShipmentRequest | None:
    """Return the customer-owned shipment request used by the workflow endpoint."""
    return (
        db.session.query(ShipmentRequest)
        .filter(
            ShipmentRequest.id == request_id,
            ShipmentRequest.gamification_customer_id == customer_id,
        )
        .first()
    )


VALID_QUOTE_RESPONSES = {"accepted", "declined"}


def record_quote_response(
    tracking_code: str, response: Any, remote_addr: str | None = None
) -> tuple[dict[str, Any], int]:
    """Record a customer's accept/decline on the latest quote for their own request."""
    if response not in VALID_QUOTE_RESPONSES:
        return {"message": "پاسخ نامعتبر است"}, 400

    try:
        resolved_request_id = str(tracking_code).strip()
        if not resolved_request_id or resolved_request_id.isdigit():
            raise ValueError
    except (TypeError, ValueError):
        return {"message": "Not found"}, 404
        return {"message": "شناسه درخواست نامعتبر است"}, 400

    shipment_request = (
        db.session.query(ShipmentRequest)
        .filter(ShipmentRequest.tracking_code == resolved_request_id)
        .with_for_update()
        .first()
    )
    if shipment_request is None:
        return {"message": "Not found"}, 404
        return {"message": "درخواست یافت نشد یا به این مشتری تعلق ندارد"}, 404

    quote_row = (
        db.session.query(ExpertQuote)
        .filter(ExpertQuote.shipment_request_id == shipment_request.id)
        .order_by(ExpertQuote.created_at.desc())
        .with_for_update()
        .first()
    )
    if quote_row is None:
        return {"message": "پیشنهاد قیمتی برای این درخواست ثبت نشده است"}, 404

    if quote_row.customer_response == response:
        return {
            "message": "Response recorded",
            "latest_quote": build_latest_quote_payload(shipment_request),
        }, 200
    if quote_row.customer_response is not None:
        return {"message": "شما قبلاً به این پیشنهاد پاسخ داده‌اید"}, 409

    if quote_row.valid_until is not None and quote_row.valid_until < date.today():
        return {"message": "مهلت این پیشنهاد به پایان رسیده است"}, 400

    try:
        quote_row.customer_response = response
        quote_row.responded_at = datetime.utcnow()
        # Surface the decision to the assigned expert on their next console visit.
        shipment_request.has_unread_for_assignee = True
        db.session.add(ExpertConsoleLog(
            shipment_request_id=shipment_request.id,
            expert_user_id=None,
            action="customer_quote_response",
            old_status=shipment_request.status,
            new_status=shipment_request.status,
            note=f"response={response}; quote_id={quote_row.id}; capability=tracking_code",
            ip_address=remote_addr,
            created_at=datetime.utcnow(),
        ))
        db.session.commit()
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        db.session.rollback()
        current_app.logger.error("Failed to record quote response: %s", exc)
        return {"message": "خطا در ثبت پاسخ"}, 500

    return {
        "message": "پاسخ شما ثبت شد",
        "latest_quote": build_latest_quote_payload(shipment_request),
    }, 200


def list_customer_workflow_step_definitions() -> list[dict[str, Any]]:
    """Return the current fixed workflow step definitions."""
    return [
        {"name": "email_verified", "order": 1, "title": "تایید ایمیل", "points": 10},
        {"name": "request_submitted", "order": 2, "title": "ارسال درخواست", "points": 20},
        {"name": "expert_assigned", "order": 3, "title": "اختصاص کارشناس", "points": 15},
        {"name": "expert_contacted", "order": 4, "title": "تماس کارشناس", "points": 25},
        {"name": "quote_provided", "order": 5, "title": "ارائه پیشنهاد", "points": 30},
        {"name": "contract_signed", "order": 6, "title": "امضای قرارداد", "points": 50},
        {"name": "shipment_picked_up", "order": 7, "title": "تحویل مرسوله", "points": 40},
        {"name": "shipment_delivered", "order": 8, "title": "تحویل به مقصد", "points": 100},
    ]


def build_workflow_step_payload(
    step_definition: dict[str, Any],
    completed_step: CustomerWorkflowStep | None,
) -> dict[str, Any]:
    """Build one workflow step entry in the current response shape."""
    return {
        "name": step_definition["name"],
        "order": step_definition["order"],
        "title": step_definition["title"],
        "points": step_definition["points"],
        "is_completed": completed_step.is_completed if completed_step else False,
        "completed_at": (
            completed_step.completed_at.isoformat()
            if completed_step and completed_step.completed_at
            else None
        ),
        "points_earned": completed_step.points_earned if completed_step else 0,
    }


def build_assigned_expert_payload(shipment_request: ShipmentRequest) -> dict[str, Any] | None:
    """Build the assigned expert object used by the workflow response."""
    if not shipment_request.assigned_expert:
        return None

    expert = shipment_request.assigned_expert
    return {
        "id": expert.id,
        "full_name": expert.full_name,
        "phone": expert.phone or "",
        "email": expert.email or "",
    }


def build_latest_quote_payload(shipment_request: ShipmentRequest) -> dict[str, Any] | None:
    """Build the latest quote object used by the workflow response."""
    quote_row = (
        db.session.query(ExpertQuote)
        .filter(ExpertQuote.shipment_request_id == shipment_request.id)
        .order_by(ExpertQuote.created_at.desc())
        .first()
    )
    if not quote_row:
        return None

    return {
        "amount": int(quote_row.amount) if quote_row.amount is not None else None,
        "currency": quote_row.currency or "IRR",
        "note": quote_row.note,
        "valid_until": quote_row.valid_until.isoformat() if quote_row.valid_until else None,
        "created_at": (
            quote_row.created_at.isoformat()
            if hasattr(quote_row.created_at, "isoformat")
            else str(quote_row.created_at)
        ),
        "customer_response": quote_row.customer_response,
        "responded_at": quote_row.responded_at.isoformat() if quote_row.responded_at else None,
    }


def build_customer_workflow_payload(
    shipment_request: ShipmentRequest,
    customer_id: int,
    request_id: int,
) -> dict[str, Any]:
    """Build the current customer workflow response shape."""
    steps = (
        db.session.query(CustomerWorkflowStep)
        .filter(
            CustomerWorkflowStep.customer_id == customer_id,
            CustomerWorkflowStep.shipment_request_id == request_id,
        )
        .order_by(CustomerWorkflowStep.step_order)
        .all()
    )

    all_steps = list_customer_workflow_step_definitions()
    workflow_status = [
        build_workflow_step_payload(
            step_definition,
            next((step for step in steps if step.step_name == step_definition["name"]), None),
        )
        for step_definition in all_steps
    ]

    created_at = serialize_legacy_utc_datetime(shipment_request.created_at)

    return {
        "id": shipment_request.id,
        "shipping_type": shipment_request.shipping_type or "domestic",
        "status": shipment_request.status or "new",
        "created_at": created_at,
        "assigned_expert": build_assigned_expert_payload(shipment_request),
        "customer_id": customer_id,
        "request_id": request_id,
        "tracking_code": shipment_request.tracking_code,
        "workflow_steps": workflow_status,
        "workflow_steps_simple": _workflow_steps_simple_4(shipment_request),
        "total_points_earned": sum(step.points_earned for step in steps),
        "completed_steps": len([step for step in steps if step.is_completed]),
        "total_steps": len(all_steps),
        "latest_quote": build_latest_quote_payload(shipment_request),
    }


def get_customer_workflow_payload(customer_id: int, request_id: int) -> dict[str, Any] | None:
    """Return the public workflow payload, or None when ownership lookup fails."""
    shipment_request = get_customer_workflow_or_none(customer_id, request_id)
    if shipment_request is None:
        return None

    return build_customer_workflow_payload(shipment_request, customer_id, request_id)


def build_leaderboard_entry(customer: CustomerGamification, rank: int) -> dict[str, Any]:
    """Build the current leaderboard entry response shape."""
    return {
        "rank": rank,
        "customer_id": customer.id,
        "name": f"{customer.first_name or ''} {customer.last_name or ''}".strip() or "کاربر ناشناس",
        "loyalty_points": customer.loyalty_points,
        "customer_level": customer.customer_level,
        "total_requests": customer.total_requests,
        "completed_requests": customer.completed_requests,
    }


def list_leaderboard_payload() -> dict[str, Any]:
    """Return the current leaderboard payload."""
    customers = (
        db.session.query(CustomerGamification)
        .filter(CustomerGamification.is_email_verified == True)
        .order_by(CustomerGamification.loyalty_points.desc())
        .limit(20)
        .all()
    )

    return {
        "leaderboard": [
            build_leaderboard_entry(customer, rank)
            for rank, customer in enumerate(customers, 1)
        ],
        "total_customers": len(customers),
    }
