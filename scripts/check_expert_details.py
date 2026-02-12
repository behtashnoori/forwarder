#!/usr/bin/env python3
"""
Check expert user details
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app
from backend.models import ExpertUser
from backend.extensions import db

def check_expert_details():
    """Check expert user details."""
    app = create_app()
    
    with app.app_context():
        try:
            experts = ExpertUser.query.all()
            
            if not experts:
                print("❌ No expert users found in database")
                return
            
            print(f"✅ Found {len(experts)} expert users:")
            print("=" * 50)
            
            for expert in experts:
                print(f"ID: {expert.id}")
                print(f"Username: {expert.username}")
                print(f"Full Name: {expert.full_name}")
                print(f"Email: {expert.email}")
                print(f"Role: {expert.role}")
                print(f"Active: {expert.is_active}")
                print(f"Created: {expert.created_at}")
                print(f"Last Login: {expert.last_login_at}")
                print(f"Password Hash: {expert.password_hash[:20]}..." if expert.password_hash else "No password hash")
                print("-" * 30)
            
        except Exception as e:
            print(f"❌ Error checking expert details: {e}")

if __name__ == "__main__":
    check_expert_details()
