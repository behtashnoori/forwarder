"""Seed script to create CRM hierarchy data."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import bcrypt
from __init__ import create_app
from models import ExpertUser, TransportMethod, ExpertSpecialization, AssignmentRule
from extensions import db

def seed_crm_hierarchy():
    """Create CRM hierarchy data."""
    app = create_app()
    
    with app.app_context():
        # Create transport methods
        transport_methods = [
            {
                "name": "road_transport",
                "name_fa": "حمل و نقل جاده‌ای",
                "description": "حمل و نقل از طریق جاده با کامیون و وانت"
            },
            {
                "name": "rail_transport", 
                "name_fa": "حمل و نقل ریلی",
                "description": "حمل و نقل از طریق راه‌آهن"
            },
            {
                "name": "air_transport",
                "name_fa": "حمل و نقل هوایی", 
                "description": "حمل و نقل از طریق هواپیما"
            },
            {
                "name": "sea_transport",
                "name_fa": "حمل و نقل دریایی",
                "description": "حمل و نقل از طریق کشتی"
            },
            {
                "name": "express_delivery",
                "name_fa": "پیک سریع",
                "description": "حمل و نقل سریع برای بسته‌های کوچک"
            }
        ]
        
        for method_data in transport_methods:
            existing = db.session.query(TransportMethod).filter(
                TransportMethod.name == method_data["name"]
            ).first()
            
            if not existing:
                transport_method = TransportMethod(
                    name=method_data["name"],
                    name_fa=method_data["name_fa"],
                    description=method_data["description"],
                    is_active=True
                )
                db.session.add(transport_method)
        
        # Create CRM Manager
        crm_manager = db.session.query(ExpertUser).filter(
            ExpertUser.username == "crm_manager"
        ).first()
        
        if not crm_manager:
            password_hash = bcrypt.hashpw("crm123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            crm_manager = ExpertUser(
                username="crm_manager",
                password_hash=password_hash,
                full_name="مدیر CRM",
                email="crm.manager@company.com",
                phone="09123456792",
                role="crm_manager",
                department="crm",
                is_active=True
            )
            db.session.add(crm_manager)
        
        # Create Business Experts
        business_experts = [
            {
                "username": "business_expert1",
                "password": "business123",
                "full_name": "کارشناس بازرگانی اول",
                "email": "business.expert1@company.com",
                "phone": "09123456793",
                "specializations": ["road_transport", "express_delivery"]
            },
            {
                "username": "business_expert2", 
                "password": "business123",
                "full_name": "کارشناس بازرگانی دوم",
                "email": "business.expert2@company.com",
                "phone": "09123456794",
                "specializations": ["air_transport", "sea_transport"]
            },
            {
                "username": "business_expert3",
                "password": "business123", 
                "full_name": "کارشناس بازرگانی سوم",
                "email": "business.expert3@company.com",
                "phone": "09123456795",
                "specializations": ["rail_transport", "road_transport"]
            }
        ]
        
        for expert_data in business_experts:
            existing = db.session.query(ExpertUser).filter(
                ExpertUser.username == expert_data["username"]
            ).first()
            
            if not existing:
                password_hash = bcrypt.hashpw(expert_data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                expert = ExpertUser(
                    username=expert_data["username"],
                    password_hash=password_hash,
                    full_name=expert_data["full_name"],
                    email=expert_data["email"],
                    phone=expert_data["phone"],
                    role="business_expert",
                    department="business",
                    manager_id=crm_manager.id,
                    is_active=True
                )
                db.session.add(expert)
                db.session.flush()
                
                # Add specializations
                for spec_name in expert_data["specializations"]:
                    transport_method = db.session.query(TransportMethod).filter(
                        TransportMethod.name == spec_name
                    ).first()
                    
                    if transport_method:
                        specialization = ExpertSpecialization(
                            expert_user_id=expert.id,
                            transport_method_id=transport_method.id,
                            proficiency_level="advanced",
                            is_primary=(spec_name == expert_data["specializations"][0])  # First one is primary
                        )
                        db.session.add(specialization)
        
        # Create Assignment Rules
        assignment_rules = [
            {
                "name": "ارجاع بر اساس روش حمل",
                "description": "ارجاع خودکار درخواست‌ها بر اساس تخصص کارشناسان در روش‌های حمل",
                "rule_type": "transport_method",
                "conditions": {
                    "priority_methods": ["air_transport", "express_delivery"],
                    "fallback_enabled": True
                },
                "priority": 10
            },
            {
                "name": "توزیع بار کاری",
                "description": "ارجاع به کارشناسانی که کمترین بار کاری را دارند",
                "rule_type": "workload", 
                "conditions": {
                    "max_workload": 5,
                    "consider_specialization": True
                },
                "priority": 5
            },
            {
                "name": "ارجاع بر اساس اولویت",
                "description": "ارجاع درخواست‌های با اولویت بالا به کارشناسان ارشد",
                "rule_type": "priority",
                "conditions": {
                    "high_priority_experts": ["business_expert1", "business_expert2"],
                    "normal_priority_all": True
                },
                "priority": 8
            }
        ]
        
        for rule_data in assignment_rules:
            existing = db.session.query(AssignmentRule).filter(
                AssignmentRule.name == rule_data["name"]
            ).first()
            
            if not existing:
                rule = AssignmentRule(
                    name=rule_data["name"],
                    description=rule_data["description"],
                    rule_type=rule_data["rule_type"],
                    conditions=str(rule_data["conditions"]).replace("'", '"'),
                    priority=rule_data["priority"],
                    is_active=True,
                    created_by=crm_manager.id
                )
                db.session.add(rule)
        
        db.session.commit()
        print("CRM hierarchy data seeded successfully!")

if __name__ == "__main__":
    seed_crm_hierarchy()
