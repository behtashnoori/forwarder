"""User management API routes for CRM hierarchy system."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import (
    ExpertUser, TransportMethod, ExpertSpecialization, AssignmentRule, AssignmentLog
)
from backend.auth import require_auth, get_current_user
from backend.security import validate_input, sanitize_input

user_management_bp = Blueprint("user_management", __name__, url_prefix="/api/user-management")


# Transport Methods Management
@user_management_bp.get("/transport-methods")
@require_auth
def get_transport_methods():
    """Get all transport methods."""
    try:
        transport_methods = db.session.query(TransportMethod).filter(
            TransportMethod.is_active == True
        ).order_by(TransportMethod.name_fa).all()
        
        methods_data = []
        for method in transport_methods:
            methods_data.append({
                "id": method.id,
                "name": method.name,
                "name_fa": method.name_fa,
                "description": method.description,
                "is_active": method.is_active,
                "created_at": method.created_at.isoformat()
            })
        
        return jsonify({
            "transport_methods": methods_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting transport methods: {e}")
        return jsonify({"error": "خطا در دریافت روش‌های حمل"}), 500


@user_management_bp.post("/transport-methods")
@require_auth
def create_transport_method():
    """Create a new transport method."""
    try:
        current_user = get_current_user()
        if current_user.role not in ["admin", "crm_manager"]:
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        data = request.get_json()
        
        transport_method = TransportMethod(
            name=data.get("name"),
            name_fa=data.get("name_fa"),
            description=data.get("description"),
            is_active=data.get("is_active", True)
        )
        
        db.session.add(transport_method)
        db.session.commit()
        
        return jsonify({
            "message": "روش حمل با موفقیت ایجاد شد",
            "transport_method_id": transport_method.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating transport method: {e}")
        return jsonify({"error": "خطا در ایجاد روش حمل"}), 500


# User Management
@user_management_bp.get("/users")
@require_auth
def get_users():
    """Get all users with hierarchy information."""
    try:
        current_user = get_current_user()
        
        # Build query based on user role
        query = db.session.query(ExpertUser)
        
        if current_user.role == "crm_manager":
            # CRM managers can see their subordinates
            query = query.filter(
                or_(
                    ExpertUser.manager_id == current_user.id,
                    ExpertUser.id == current_user.id
                )
            )
        elif current_user.role == "admin":
            # Admins can see all users
            pass
        else:
            # Other users can only see themselves
            query = query.filter(ExpertUser.id == current_user.id)
        
        users = query.order_by(ExpertUser.full_name).all()
        
        users_data = []
        for user in users:
            # Get specializations
            specializations = []
            for spec in user.specializations:
                specializations.append({
                    "id": spec.id,
                    "transport_method": {
                        "id": spec.transport_method.id,
                        "name": spec.transport_method.name_fa
                    },
                    "proficiency_level": spec.proficiency_level,
                    "is_primary": spec.is_primary
                })
            
            # Get manager info
            manager_info = None
            if user.manager:
                manager_info = {
                    "id": user.manager.id,
                    "name": user.manager.full_name
                }
            
            # Get subordinates count
            subordinates_count = len(user.subordinates) if user.subordinates else 0
            
            users_data.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "department": user.department,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "manager": manager_info,
                "subordinates_count": subordinates_count,
                "specializations": specializations,
                "workload": user.get_workload()
            })
        
        return jsonify({
            "users": users_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting users: {e}")
        return jsonify({"error": "خطا در دریافت کاربران"}), 500


@user_management_bp.post("/users")
@require_auth
def create_user():
    """Create a new user."""
    try:
        current_user = get_current_user()
        if current_user.role not in ["admin", "crm_manager"]:
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        data = request.get_json()
        
        # Validate role hierarchy
        new_role = data.get("role")
        if current_user.role == "crm_manager" and new_role not in ["business_expert", "expert"]:
            return jsonify({"error": "شما فقط می‌توانید کارشناس بازرگانی و کارشناس ایجاد کنید"}), 400
        
        # Create user
        user = ExpertUser(
            username=data.get("username"),
            password_hash=data.get("password_hash"),  # Should be hashed on frontend
            full_name=data.get("full_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            role=new_role,
            department=data.get("department"),
            manager_id=current_user.id if current_user.role == "crm_manager" else data.get("manager_id"),
            is_active=data.get("is_active", True)
        )
        
        db.session.add(user)
        db.session.flush()
        
        # Add specializations
        specializations = data.get("specializations", [])
        for spec_data in specializations:
            specialization = ExpertSpecialization(
                expert_user_id=user.id,
                transport_method_id=spec_data.get("transport_method_id"),
                proficiency_level=spec_data.get("proficiency_level", "intermediate"),
                is_primary=spec_data.get("is_primary", False)
            )
            db.session.add(specialization)
        
        db.session.commit()
        
        return jsonify({
            "message": "کاربر با موفقیت ایجاد شد",
            "user_id": user.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {e}")
        return jsonify({"error": "خطا در ایجاد کاربر"}), 500


@user_management_bp.put("/users/<int:user_id>")
@require_auth
def update_user(user_id: int):
    """Update user information."""
    try:
        current_user = get_current_user()
        
        # Check permissions
        if current_user.role not in ["admin", "crm_manager"]:
            if current_user.id != user_id:
                return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        user = db.session.query(ExpertUser).get(user_id)
        if not user:
            return jsonify({"error": "کاربر یافت نشد"}), 404
        
        # Check hierarchy permissions
        if current_user.role == "crm_manager":
            if user.manager_id != current_user.id and user.id != current_user.id:
                return jsonify({"error": "شما فقط می‌توانید زیردستان خود را ویرایش کنید"}), 403
        
        data = request.get_json()
        
        # Update basic fields
        updatable_fields = ["full_name", "email", "phone", "department", "is_active"]
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Update role (only admins and CRM managers)
        if current_user.role in ["admin", "crm_manager"] and "role" in data:
            user.role = data["role"]
        
        # Update manager (only admins)
        if current_user.role == "admin" and "manager_id" in data:
            user.manager_id = data["manager_id"]
        
        # Update specializations
        if "specializations" in data:
            # Remove existing specializations
            db.session.query(ExpertSpecialization).filter(
                ExpertSpecialization.expert_user_id == user_id
            ).delete()
            
            # Add new specializations
            for spec_data in data["specializations"]:
                specialization = ExpertSpecialization(
                    expert_user_id=user_id,
                    transport_method_id=spec_data.get("transport_method_id"),
                    proficiency_level=spec_data.get("proficiency_level", "intermediate"),
                    is_primary=spec_data.get("is_primary", False)
                )
                db.session.add(specialization)
        
        db.session.commit()
        
        return jsonify({
            "message": "اطلاعات کاربر به‌روزرسانی شد"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی کاربر"}), 500


# Assignment Rules Management
@user_management_bp.get("/assignment-rules")
@require_auth
def get_assignment_rules():
    """Get all assignment rules."""
    try:
        current_user = get_current_user()
        if current_user.role not in ["admin", "crm_manager"]:
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        rules = db.session.query(AssignmentRule).order_by(
            desc(AssignmentRule.priority), AssignmentRule.name
        ).all()
        
        rules_data = []
        for rule in rules:
            rules_data.append({
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "rule_type": rule.rule_type,
                "conditions": json.loads(rule.conditions),
                "priority": rule.priority,
                "is_active": rule.is_active,
                "created_by": {
                    "id": rule.creator.id,
                    "name": rule.creator.full_name
                },
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat()
            })
        
        return jsonify({
            "assignment_rules": rules_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting assignment rules: {e}")
        return jsonify({"error": "خطا در دریافت قوانین ارجاع"}), 500


@user_management_bp.post("/assignment-rules")
@require_auth
def create_assignment_rule():
    """Create a new assignment rule."""
    try:
        current_user = get_current_user()
        if current_user.role not in ["admin", "crm_manager"]:
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        data = request.get_json()
        
        rule = AssignmentRule(
            name=data.get("name"),
            description=data.get("description"),
            rule_type=data.get("rule_type"),
            conditions=json.dumps(data.get("conditions", {})),
            priority=data.get("priority", 1),
            is_active=data.get("is_active", True),
            created_by=current_user.id
        )
        
        db.session.add(rule)
        db.session.commit()
        
        return jsonify({
            "message": "قانون ارجاع با موفقیت ایجاد شد",
            "rule_id": rule.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating assignment rule: {e}")
        return jsonify({"error": "خطا در ایجاد قانون ارجاع"}), 500


@user_management_bp.put("/assignment-rules/<int:rule_id>")
@require_auth
def update_assignment_rule(rule_id: int):
    """Update an assignment rule."""
    try:
        current_user = get_current_user()
        if current_user.role not in ["admin", "crm_manager"]:
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        rule = db.session.query(AssignmentRule).get(rule_id)
        if not rule:
            return jsonify({"error": "قانون ارجاع یافت نشد"}), 404
        
        data = request.get_json()
        
        # Update fields
        updatable_fields = ["name", "description", "rule_type", "priority", "is_active"]
        for field in updatable_fields:
            if field in data:
                setattr(rule, field, data[field])
        
        if "conditions" in data:
            rule.conditions = json.dumps(data["conditions"])
        
        rule.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "message": "قانون ارجاع به‌روزرسانی شد"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating assignment rule: {e}")
        return jsonify({"error": "خطا در به‌روزرسانی قانون ارجاع"}), 500


# Assignment Statistics
@user_management_bp.get("/assignment-statistics")
@require_auth
def get_assignment_statistics():
    """Get assignment statistics."""
    try:
        current_user = get_current_user()
        if current_user.role not in ["admin", "crm_manager"]:
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        from backend.assignment_engine import assignment_engine
        stats = assignment_engine.get_assignment_statistics()
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error getting assignment statistics: {e}")
        return jsonify({"error": "خطا در دریافت آمار ارجاع"}), 500


# Manual Assignment
@user_management_bp.post("/manual-assignment")
@require_auth
def manual_assignment():
    """Manually assign a request to an expert."""
    try:
        current_user = get_current_user()
        if current_user.role not in ["admin", "crm_manager", "supervisor"]:
            return jsonify({"error": "دسترسی غیرمجاز"}), 403
        
        data = request.get_json()
        request_id = data.get("request_id")
        expert_id = data.get("expert_id")
        reason = data.get("reason", "Manual assignment")
        
        if not request_id or not expert_id:
            return jsonify({"error": "شناسه درخواست و کارشناس الزامی است"}), 400
        
        from backend.assignment_engine import assignment_engine
        
        # Get the request
        from backend.models import ShipmentRequest
        request = db.session.query(ShipmentRequest).get(request_id)
        if not request:
            return jsonify({"error": "درخواست یافت نشد"}), 404
        
        # Get the expert
        expert = db.session.query(ExpertUser).get(expert_id)
        if not expert:
            return jsonify({"error": "کارشناس یافت نشد"}), 404
        
        # Check if expert is under current user's management
        if current_user.role == "crm_manager":
            if expert.manager_id != current_user.id:
                return jsonify({"error": "شما فقط می‌توانید به زیردستان خود ارجاع دهید"}), 403
        
        # Manual assignment
        request.assigned_to = expert_id
        request.status = "assigned"
        request.has_unread_for_assignee = True
        
        # Create assignment log
        log = AssignmentLog(
            shipment_request_id=request_id,
            assigned_expert_id=expert_id,
            assignment_method="manual",
            assignment_reason=reason,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            "message": "درخواست با موفقیت ارجاع داده شد"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in manual assignment: {e}")
        return jsonify({"error": "خطا در ارجاع دستی"}), 500


@user_management_bp.get("/ping")
def ping():
    """Health check endpoint for user management API."""
    return jsonify({"message": "User Management API is running"})
