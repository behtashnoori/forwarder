"""Routes for customer gamification and email verification."""
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app, url_for
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import CustomerGamification, CustomerWorkflowStep, ShipmentRequest, ExpertUser

customer_gamification_bp = Blueprint("customer_gamification", __name__, url_prefix="/api/customer")


def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(32)


def send_verification_email(email: str, token: str, customer_name: str = None) -> bool:
    """Send verification email to customer."""
    try:
        # Link must point to frontend so user is redirected to customer panel after verify
        frontend_url = (os.environ.get("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
        verification_url = f"{frontend_url}/verify-email?token={token}"
        # In a real implementation, you would use an email service like SendGrid, AWS SES, etc.
        # For now, we'll just log the email details
        
        current_app.logger.info(f"Verification email would be sent to {email}")
        current_app.logger.info(f"Verification URL: {verification_url}")
        
        # TODO: Implement actual email sending
        # Example with SendGrid:
        # sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        # message = Mail(
        #     from_email='noreply@forwarder.com',
        #     to_emails=email,
        #     subject='تایید ایمیل - سیستم فورواردر',
        #     html_content=f'<p>سلام {customer_name or "کاربر گرامی"}</p><p>برای تایید ایمیل خود روی لینک زیر کلیک کنید:</p><p><a href="{verification_url}">تایید ایمیل</a></p>'
        # )
        # response = sg.send(message)
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending verification email: {e}")
        return False


@customer_gamification_bp.post("/register")
def register_customer():
    """Register a new customer for gamification tracking."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    
    # Validate required fields
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    
    if not email or not phone:
        return jsonify({"message": "ایمیل و شماره تماس الزامی است"}), 400
    
    # Validate email format
    if "@" not in email or "." not in email:
        return jsonify({"message": "فرمت ایمیل نامعتبر است"}), 400
    
    # Validate phone format (Iranian mobile)
    if not phone.startswith("09") or len(phone) != 11 or not phone.isdigit():
        return jsonify({"message": "شماره تماس نامعتبر است"}), 400
    
    try:
        # Check if customer already exists
        existing_customer = db.session.query(CustomerGamification).filter(
            CustomerGamification.email == email
        ).first()
        
        if existing_customer:
            return jsonify({
                "message": "این ایمیل قبلاً ثبت شده است",
                "customer_id": existing_customer.id,
                "is_verified": existing_customer.is_email_verified
            }), 200
        
        # Create new customer
        verification_token = generate_verification_token()
        verification_expires = datetime.utcnow() + timedelta(hours=24)
        
        customer = CustomerGamification(
            email=email,
            phone=phone,
            first_name=first_name or None,
            last_name=last_name or None,
            email_verification_token=verification_token,
            verification_expires_at=verification_expires
        )
        
        db.session.add(customer)
        db.session.flush()
        
        # Send verification email
        customer_name = f"{first_name} {last_name}".strip() if first_name or last_name else None
        email_sent = send_verification_email(email, verification_token, customer_name)
        
        if not email_sent:
            current_app.logger.warning(f"Failed to send verification email to {email}")
        
        db.session.commit()
        
        return jsonify({
            "message": "ثبت‌نام با موفقیت انجام شد. لطفاً ایمیل خود را تایید کنید.",
            "customer_id": customer.id,
            "email_sent": email_sent
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in customer registration: {e}")
        return jsonify({"message": "خطا در ثبت‌نام"}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in customer registration: {e}")
        return jsonify({"message": "خطای داخلی سرور"}), 500


@customer_gamification_bp.get("/verify-email")
def verify_email():
    """Verify customer email with token."""
    token = request.args.get("token")
    
    if not token:
        return jsonify({"message": "توکن تایید الزامی است"}), 400
    
    try:
        customer = db.session.query(CustomerGamification).filter(
            CustomerGamification.email_verification_token == token,
            CustomerGamification.verification_expires_at > datetime.utcnow()
        ).first()
        
        if not customer:
            return jsonify({"message": "توکن تایید نامعتبر یا منقضی شده است"}), 400
        
        # Verify email
        customer.is_email_verified = True
        customer.email_verification_token = None
        customer.verification_expires_at = None
        
        # Award points for email verification
        customer.update_loyalty_points(10)
        
        # Create workflow step
        workflow_step = CustomerWorkflowStep(
            customer_id=customer.id,
            shipment_request_id=0,  # No specific request for email verification
            step_name="email_verified",
            step_order=1,
            is_completed=True,
            completed_at=datetime.utcnow(),
            points_earned=10
        )
        
        db.session.add(workflow_step)
        db.session.commit()
        
        return jsonify({
            "message": "ایمیل شما با موفقیت تایید شد! ۱۰ امتیاز دریافت کردید.",
            "customer_id": customer.id,
            "loyalty_points": customer.loyalty_points,
            "customer_level": customer.customer_level
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in email verification: {e}")
        return jsonify({"message": "خطا در تایید ایمیل"}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in email verification: {e}")
        return jsonify({"message": "خطای داخلی سرور"}), 500


@customer_gamification_bp.get("/profile/<int:customer_id>")
def get_customer_profile(customer_id: int):
    """Get customer profile with gamification data."""
    try:
        customer = db.session.query(CustomerGamification).filter(
            CustomerGamification.id == customer_id
        ).first()
        
        if not customer:
            return jsonify({"message": "مشتری یافت نشد"}), 404
        
        # Get recent workflow steps
        recent_steps = db.session.query(CustomerWorkflowStep).filter(
            CustomerWorkflowStep.customer_id == customer_id
        ).order_by(CustomerWorkflowStep.created_at.desc()).limit(10).all()
        
        # Get recent requests
        recent_requests = db.session.query(ShipmentRequest).filter(
            ShipmentRequest.gamification_customer_id == customer_id
        ).order_by(ShipmentRequest.created_at.desc()).limit(5).all()
        
        return jsonify({
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
                "created_at": customer.created_at.isoformat()
            },
            "recent_steps": [
                {
                    "step_name": step.step_name,
                    "step_order": step.step_order,
                    "is_completed": step.is_completed,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "points_earned": step.points_earned,
                    "created_at": step.created_at.isoformat()
                }
                for step in recent_steps
            ],
            "recent_requests": [
                {
                    "id": req.id,
                    "shipping_type": req.shipping_type,
                    "status": req.status,
                    "created_at": req.created_at.isoformat(),
                    "assigned_expert": {
                        "id": req.assigned_expert.id,
                        "full_name": req.assigned_expert.full_name,
                        "phone": req.assigned_expert.phone
                    } if req.assigned_expert else None
                }
                for req in recent_requests
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting customer profile: {e}")
        return jsonify({"message": "خطا در دریافت اطلاعات مشتری"}), 500


@customer_gamification_bp.get("/workflow/<int:customer_id>")
def get_customer_workflow(customer_id: int):
    """Get customer workflow steps for a specific request."""
    request_id = request.args.get("request_id")
    
    if not request_id:
        return jsonify({"message": "شناسه درخواست الزامی است"}), 400
    
    try:
        # Get workflow steps for the request
        steps = db.session.query(CustomerWorkflowStep).filter(
            CustomerWorkflowStep.customer_id == customer_id,
            CustomerWorkflowStep.shipment_request_id == request_id
        ).order_by(CustomerWorkflowStep.step_order).all()
        
        # Define all possible steps
        all_steps = [
            {"name": "email_verified", "order": 1, "title": "تایید ایمیل", "points": 10},
            {"name": "request_submitted", "order": 2, "title": "ارسال درخواست", "points": 20},
            {"name": "expert_assigned", "order": 3, "title": "اختصاص کارشناس", "points": 15},
            {"name": "expert_contacted", "order": 4, "title": "تماس کارشناس", "points": 25},
            {"name": "quote_provided", "order": 5, "title": "ارائه پیشنهاد", "points": 30},
            {"name": "contract_signed", "order": 6, "title": "امضای قرارداد", "points": 50},
            {"name": "shipment_picked_up", "order": 7, "title": "تحویل مرسوله", "points": 40},
            {"name": "shipment_delivered", "order": 8, "title": "تحویل به مقصد", "points": 100}
        ]
        
        # Create workflow status
        workflow_status = []
        for step_def in all_steps:
            completed_step = next((s for s in steps if s.step_name == step_def["name"]), None)
            
            workflow_status.append({
                "name": step_def["name"],
                "order": step_def["order"],
                "title": step_def["title"],
                "points": step_def["points"],
                "is_completed": completed_step.is_completed if completed_step else False,
                "completed_at": completed_step.completed_at.isoformat() if completed_step and completed_step.completed_at else None,
                "points_earned": completed_step.points_earned if completed_step else 0
            })
        
        return jsonify({
            "customer_id": customer_id,
            "request_id": request_id,
            "workflow_steps": workflow_status,
            "total_points_earned": sum(step.points_earned for step in steps),
            "completed_steps": len([s for s in steps if s.is_completed]),
            "total_steps": len(all_steps)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting customer workflow: {e}")
        return jsonify({"message": "خطا در دریافت گردش کار"}), 500


@customer_gamification_bp.post("/complete-step")
def complete_workflow_step():
    """Mark a workflow step as completed."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    
    customer_id = data.get("customer_id")
    request_id = data.get("request_id")
    step_name = data.get("step_name")
    
    if not all([customer_id, request_id, step_name]):
        return jsonify({"message": "تمام فیلدها الزامی است"}), 400
    
    try:
        # Check if step already exists
        existing_step = db.session.query(CustomerWorkflowStep).filter(
            CustomerWorkflowStep.customer_id == customer_id,
            CustomerWorkflowStep.shipment_request_id == request_id,
            CustomerWorkflowStep.step_name == step_name
        ).first()
        
        if existing_step and existing_step.is_completed:
            return jsonify({"message": "این مرحله قبلاً تکمیل شده است"}), 200
        
        # Define step points
        step_points = {
            "email_verified": 10,
            "request_submitted": 20,
            "expert_assigned": 15,
            "expert_contacted": 25,
            "quote_provided": 30,
            "contract_signed": 50,
            "shipment_picked_up": 40,
            "shipment_delivered": 100
        }
        
        points = step_points.get(step_name, 0)
        
        if existing_step:
            # Update existing step
            existing_step.is_completed = True
            existing_step.completed_at = datetime.utcnow()
            existing_step.points_earned = points
        else:
            # Create new step
            step_order = {
                "email_verified": 1,
                "request_submitted": 2,
                "expert_assigned": 3,
                "expert_contacted": 4,
                "quote_provided": 5,
                "contract_signed": 6,
                "shipment_picked_up": 7,
                "shipment_delivered": 8
            }.get(step_name, 0)
            
            new_step = CustomerWorkflowStep(
                customer_id=customer_id,
                shipment_request_id=request_id,
                step_name=step_name,
                step_order=step_order,
                is_completed=True,
                completed_at=datetime.utcnow(),
                points_earned=points
            )
            db.session.add(new_step)
        
        # Update customer loyalty points
        customer = db.session.query(CustomerGamification).filter(
            CustomerGamification.id == customer_id
        ).first()
        
        if customer:
            customer.update_loyalty_points(points)
        
        db.session.commit()
        
        return jsonify({
            "message": f"مرحله {step_name} با موفقیت تکمیل شد! {points} امتیاز دریافت کردید.",
            "points_earned": points,
            "total_points": customer.loyalty_points if customer else 0,
            "customer_level": customer.customer_level if customer else "bronze"
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error completing workflow step: {e}")
        return jsonify({"message": "خطا در تکمیل مرحله"}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing workflow step: {e}")
        return jsonify({"message": "خطای داخلی سرور"}), 500


@customer_gamification_bp.get("/leaderboard")
def get_leaderboard():
    """Get customer leaderboard based on loyalty points."""
    try:
        customers = db.session.query(CustomerGamification).filter(
            CustomerGamification.is_email_verified == True
        ).order_by(CustomerGamification.loyalty_points.desc()).limit(20).all()
        
        leaderboard = []
        for i, customer in enumerate(customers, 1):
            leaderboard.append({
                "rank": i,
                "customer_id": customer.id,
                "name": f"{customer.first_name or ''} {customer.last_name or ''}".strip() or "کاربر ناشناس",
                "loyalty_points": customer.loyalty_points,
                "customer_level": customer.customer_level,
                "total_requests": customer.total_requests,
                "completed_requests": customer.completed_requests
            })
        
        return jsonify({
            "leaderboard": leaderboard,
            "total_customers": len(customers)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting leaderboard: {e}")
        return jsonify({"message": "خطا در دریافت جدول امتیازات"}), 500
