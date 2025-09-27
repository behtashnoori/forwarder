"""Seed script to create sample expert users."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import bcrypt
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
        
        # Hash the default password
        default_password = "expert123"
        password_hash = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create sample experts
        experts = [
            {
                "username": "expert",
                "password": "expert123",
                "full_name": "کارشناس اول",
                "email": "expert@company.com",
                "phone": "09123456789",
                "role": "expert"
            },
            {
                "username": "expert1",
                "password": "expert123", 
                "full_name": "کارشناس اول",
                "email": "expert1@company.com",
                "phone": "09123456789",
                "role": "expert"
            },
            {
                "username": "expert2", 
                "password": "expert123",
                "full_name": "کارشناس دوم",
                "email": "expert2@company.com",
                "phone": "09123456790",
                "role": "expert"
            },
            {
                "username": "supervisor",
                "password": "admin123",
                "full_name": "سرپرست تیم",
                "email": "supervisor@company.com", 
                "phone": "09123456791",
                "role": "supervisor"
            }
        ]
        
        for expert_data in experts:
            # Hash each user's password
            user_password_hash = bcrypt.hashpw(expert_data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            expert = ExpertUser(
                username=expert_data["username"],
                password_hash=user_password_hash,
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
