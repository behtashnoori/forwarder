#!/usr/bin/env python3

"""
Check Expert Users Script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app
from backend.models_expert_console import ExpertUser

def check_expert_users():
    """Check existing expert users."""
    app = create_app()
    
    with app.app_context():
        try:
            experts = ExpertUser.query.all()
            
            if not experts:
                print("❌ No expert users found in database")
                return False
            
            print(f"✅ Found {len(experts)} expert user(s):")
            for expert in experts:
                print(f"   ID: {expert.id}")
                print(f"   Username: {expert.username}")
                print(f"   Full Name: {expert.full_name}")
                print(f"   Email: {expert.email}")
                print(f"   Role: {expert.role}")
                print(f"   Active: {expert.is_active}")
                print(f"   Created: {expert.created_at}")
                print(f"   Last Login: {expert.last_login_at}")
                print("   " + "-" * 40)
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking expert users: {e}")
            return False

if __name__ == '__main__':
    check_expert_users()
