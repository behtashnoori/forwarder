"""Routes for shipment request creation."""
import secrets
import string
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import ShipmentRequest, ShipmentRequestLog, TransportMethod, CustomerGamification, CustomerWorkflowStep
from backend.referral_engine import referral_engine

shipment_request_bp = Blueprint("shipment_request", __name__, url_prefix="/api")


@shipment_request_bp.get("/transport-methods")
def get_transport_methods():
    """Get available transport methods for international and domestic shipping."""
    try:
        # Get all active transport methods
        methods = db.session.query(TransportMethod).filter(TransportMethod.is_active == True).all()
        
        # Categorize methods based on their names
        international_methods = []
        domestic_methods = []
        
        for method in methods:
            method_data = {
                "id": method.id,
                "name": method.name,
                "name_fa": method.name_fa,
                "description": method.description
            }
            
            # Categorize based on method name
            method_name_lower = method.name.lower()
            
            # Check for international methods
            if method_name_lower in ["sea freight", "air freight", "land transport", "rail transport"]:
                international_methods.append(method_data)
            
            # Check for domestic methods (separate if to allow overlap)
            if method_name_lower in ["road transport", "rail transport", "air transport"]:
                domestic_methods.append(method_data)
            
            # If method doesn't match any category, add to both
            if (method_name_lower not in ["sea freight", "air freight", "land transport", "rail transport"] and 
                method_name_lower not in ["road transport", "rail transport", "air transport"]):
                international_methods.append(method_data)
                domestic_methods.append(method_data)
        
        return jsonify({
            "international_methods": international_methods,
            "domestic_methods": domestic_methods,
            "preference_options": [
                {"value": "customer_choice", "label": "انتخاب مشتری", "description": "مشتری روش حمل را انتخاب می‌کند"},
                {"value": "forwarder_suggestion", "label": "پیشنهاد فورواردر", "description": "فورواردر بهترین روش را پیشنهاد می‌دهد"}
            ]
        })
        
    except Exception:
        current_app.logger.exception("Error fetching transport methods")
        return jsonify({"message": "خطا در دریافت روش‌های حمل"}), 500

@shipment_request_bp.post("/shipment-request")
def create_shipment_request():
    """Create a shipment request from public form submissions."""
    data: Dict[str, Any] = request.get_json(silent=True) or {}

    # Determine shipping type
    shipping_type = data.get("shipping_type", "domestic")
    if shipping_type not in ["domestic", "international"]:
        return (
            jsonify({"message": "نوع ارسال نامعتبر است."}),
            400,
        )

    # Validate location data based on shipping type
    if shipping_type == "domestic":
        try:
            origin_province_id = int(data["origin_province_id"])
            origin_county_id = int(data["origin_county_id"])
            origin_city_id = int(data["origin_city_id"])
            dest_province_id = int(data["dest_province_id"])
            dest_county_id = int(data["dest_county_id"])
            dest_city_id = int(data["dest_city_id"])
        except (KeyError, TypeError, ValueError):
            return (
                jsonify({"message": "اطلاعات مبدا و مقصد داخلی نامعتبر است."}),
                400,
            )
    else:  # international
        origin_country = data.get("origin_country", "").strip()
        origin_city_international = data.get("origin_city_international", "").strip()
        dest_country = data.get("dest_country", "").strip()
        dest_city_international = data.get("dest_city_international", "").strip()
        
        if not origin_country or not origin_city_international or not dest_country or not dest_city_international:
            return (
                jsonify({"message": "اطلاعات مبدا و مقصد بین‌المللی نامعتبر است."}),
                400,
            )

    contact_phone = data.get("contact_phone", "")
    if not _is_valid_phone(contact_phone):
        return (
            jsonify({
                "message": "شماره تماس نامعتبر است. لطفاً شماره‌ای با پیش‌شماره 09 و ۱۱ رقم وارد کنید.",
            }),
            400,
        )

    # Customer details (optional)
    customer_first_name = data.get("customer_first_name", "").strip() or None
    customer_last_name = data.get("customer_last_name", "").strip() or None
    
    # Gamification customer ID (optional)
    gamification_customer_id = data.get("gamification_customer_id")

    # Handle transport methods - support both legacy and new format
    transport_method_raw = data.get("transport_method") or data.get("shipment_mode")
    transport_method = None
    if isinstance(transport_method_raw, str):
        sanitized = transport_method_raw.strip()
        if sanitized:
            transport_method = sanitized.lower()
    
    # New separate transport methods
    international_transport_method = data.get("international_transport_method")
    domestic_transport_method = data.get("domestic_transport_method")
    transport_method_preference = data.get("transport_method_preference", "customer_choice")
    
    # Validate transport method preference
    if transport_method_preference not in ["customer_choice", "forwarder_suggestion"]:
        transport_method_preference = "customer_choice"

    # Process cargo details (optional)
    cargo_description = data.get("cargo_description", "").strip() or None
    cargo_weight = data.get("cargo_weight")
    cargo_volume = data.get("cargo_volume")
    cargo_value = data.get("cargo_value")
    special_instructions = data.get("special_instructions", "").strip() or None
    pickup_date = data.get("pickup_date")
    delivery_date = data.get("delivery_date")

    # Convert numeric fields
    if cargo_weight is not None:
        try:
            cargo_weight = float(cargo_weight)
        except (ValueError, TypeError):
            cargo_weight = None

    if cargo_volume is not None:
        try:
            cargo_volume = float(cargo_volume)
        except (ValueError, TypeError):
            cargo_volume = None

    if cargo_value is not None:
        try:
            cargo_value = float(cargo_value)
        except (ValueError, TypeError):
            cargo_value = None

    # Convert date fields
    pickup_date_obj = None
    delivery_date_obj = None
    if pickup_date:
        try:
            pickup_date_obj = datetime.strptime(pickup_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pickup_date_obj = None

    if delivery_date:
        try:
            delivery_date_obj = datetime.strptime(delivery_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            delivery_date_obj = None

    timestamp = datetime.utcnow()

    try:
        # Create shipment request with appropriate fields based on shipping type
        shipment_request_data = {
            "shipping_type": shipping_type,
            "contact_phone": contact_phone,
            "customer_first_name": customer_first_name,
            "customer_last_name": customer_last_name,
            "transport_method": transport_method,  # Legacy field
            "international_transport_method": international_transport_method,
            "domestic_transport_method": domestic_transport_method,
            "transport_method_preference": transport_method_preference,
            "cargo_description": cargo_description,
            "cargo_weight": cargo_weight,
            "cargo_volume": cargo_volume,
            "cargo_value": cargo_value,
            "special_instructions": special_instructions,
            "pickup_date": pickup_date_obj,
            "delivery_date": delivery_date_obj,
            "created_at": timestamp,
            "ready_at": timestamp,
            "status_request_status": "new",
            # Expert Console fields with default values
            "assigned_to": None,
            "status": "new",
            "sla_due_at": None,
            "last_customer_touch_at": None,
            "has_unread_for_assignee": True,
            "priority": "normal",
            "estimated_value": None,
            "customer_id": None,  # Will be set later when customer is created
            "gamification_customer_id": gamification_customer_id,
        }

        # Add location fields based on shipping type
        if shipping_type == "domestic":
            shipment_request_data.update({
                "origin_province_id": origin_province_id,
                "origin_county_id": origin_county_id,
                "origin_city_id": origin_city_id,
                "dest_province_id": dest_province_id,
                "dest_county_id": dest_county_id,
                "dest_city_id": dest_city_id,
            })
        else:  # international
            shipment_request_data.update({
                "origin_country": origin_country,
                "origin_city_international": origin_city_international,
                "origin_address_international": data.get("origin_address_international", "").strip() or None,
                "dest_country": dest_country,
                "dest_city_international": dest_city_international,
                "dest_address_international": data.get("dest_address_international", "").strip() or None,
            })

        shipment_request = ShipmentRequest(**shipment_request_data)
        db.session.add(shipment_request)
        db.session.flush()

        # Generate unique non-guessable tracking code for public tracking (if column exists)
        try:
            alphabet = string.ascii_uppercase + string.digits
            for _ in range(100):
                code = "SR-" + "".join(secrets.choice(alphabet) for _ in range(6))
                if db.session.query(ShipmentRequest).filter(ShipmentRequest.tracking_code == code).first() is None:
                    shipment_request.tracking_code = code
                    break
            else:
                shipment_request.tracking_code = "SR-" + secrets.token_hex(3).upper()
        except Exception:
            # Fallback if tracking_code column missing or any DB error (e.g. before migration)
            shipment_request.tracking_code = f"SR{shipment_request.id:06d}"

        log_entry = ShipmentRequestLog(
            shipment_request_id=shipment_request.id,
            created_at=timestamp,
            note="ثبت اولیه درخواست",
            ip_address=request.remote_addr,
        )
        db.session.add(log_entry)
        
        # Handle gamification if customer is registered
        if gamification_customer_id:
            try:
                # Update customer request count
                customer = db.session.query(CustomerGamification).filter(
                    CustomerGamification.id == gamification_customer_id
                ).first()
                
                if customer:
                    customer.total_requests += 1
                    
                    # Create workflow step for request submission
                    workflow_step = CustomerWorkflowStep(
                        customer_id=gamification_customer_id,
                        shipment_request_id=shipment_request.id,
                        step_name="request_submitted",
                        step_order=2,
                        is_completed=True,
                        completed_at=timestamp,
                        points_earned=20
                    )
                    db.session.add(workflow_step)
                    
                    # Award points for request submission
                    customer.update_loyalty_points(20)
                    
                    current_app.logger.info(f"Gamification: Customer {gamification_customer_id} submitted request {shipment_request.id}, earned 20 points")
                    
            except Exception as e:
                current_app.logger.error(f"Error in gamification for request {shipment_request.id}: {e}")
                # Don't fail the request creation if gamification fails
        
        db.session.commit()
        
        # Try referral-based automatic assignment (one request -> one expert; distribution by rule strategy)
        try:
            assigned_expert_id = referral_engine.auto_assign_request(shipment_request.id)
            if assigned_expert_id:
                current_app.logger.info(f"Request {shipment_request.id} assigned to expert {assigned_expert_id} via referral rules")
            else:
                current_app.logger.info(f"No referral rule matched or no expert selected for request {shipment_request.id}; status remains new")
        except Exception as e:
            current_app.logger.error(f"Error in referral assignment for request {shipment_request.id}: {e}")
            # Don't fail the request creation if assignment fails
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to create shipment request")
        current_app.logger.error(f"Error details: {str(e)}")
        return (
            jsonify({"message": f"خطای داخلی سرور: {str(e)}"}),
            500,
        )

    tracking_display = getattr(shipment_request, "tracking_code", None) or f"SR{shipment_request.id:06d}"
    return (
        jsonify(
            {
                "message": "درخواست شما ثبت شد. کارشناسان ما ظرف دو ساعت با شما تماس خواهند گرفت.",
                "id": shipment_request.id,
                "tracking_code": tracking_display,
            }
        ),
        201,
    )


@shipment_request_bp.get("/shipment-request/ping")
def ping():
    """Health check endpoint for the shipment request blueprint."""
    return jsonify({"message": "pong"})


def _is_valid_phone(phone: str) -> bool:
    """Validate Iranian mobile phone number format."""
    if not isinstance(phone, str):
        return False
    return phone.startswith("09") and len(phone) == 11 and phone.isdigit()
