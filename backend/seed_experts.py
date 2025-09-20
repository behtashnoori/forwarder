"""Seed script to create sample expert users."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from __init__ import create_app
from models import ExpertUser
from extensions import db

def seed_experts():
    """Create sample expert users."""
    app = create_app()
    
    with app.app_context():
        # Check if experts already exist
        if ExpertUser.query.count() > 0:
            print("Expert users already exist. Skipping seed.")
            return
        
        # Create sample experts
        experts = [
            {
                "username": "expert1",
                "full_name": "کارشناس اول",
                "email": "expert1@company.com",
                "phone": "09123456789",
                "role": "expert"
            },
            {
                "username": "expert2", 
                "full_name": "کارشناس دوم",
                "email": "expert2@company.com",
                "phone": "09123456790",
                "role": "expert"
            },
            {
                "username": "supervisor",
                "full_name": "سرپرست تیم",
                "email": "supervisor@company.com", 
                "phone": "09123456791",
                "role": "supervisor"
            }
        ]
        
        for expert_data in experts:
            expert = ExpertUser(
                username=expert_data["username"],
                full_name=expert_data["full_name"],
                email=expert_data["email"],
                phone=expert_data["phone"],
                role=expert_data["role"],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(expert)
        
        db.session.commit()
        print("Sample expert users created successfully!")

if __name__ == "__main__":
    seed_experts()
