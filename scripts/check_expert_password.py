#!/usr/bin/env python3

"""
Check Expert User Password
"""

import psycopg2
import bcrypt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser

def check_expert_password():
    """Check expert user password."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get expert1 user
            expert = ExpertUser.query.filter_by(username='expert1').first()
            if not expert:
                print("❌ Expert user 'expert1' not found!")
                return False
            
            print(f"✅ Found expert user: {expert.username}")
            print(f"   ID: {expert.id}")
            print(f"   Full Name: {expert.full_name}")
            print(f"   Email: {expert.email}")
            print(f"   Role: {expert.role}")
            print(f"   Active: {expert.is_active}")
            print(f"   Password Hash: {expert.password_hash[:50]}...")
            
            # Test password verification
            test_passwords = ['expert123', 'password123', 'expert', 'test']
            
            for password in test_passwords:
                try:
                    if expert.password_hash and bcrypt.checkpw(password.encode('utf-8'), expert.password_hash.encode('utf-8')):
                        print(f"✅ Password '{password}' is CORRECT!")
                        return True
                    else:
                        print(f"❌ Password '{password}' is incorrect")
                except Exception as e:
                    print(f"❌ Error checking password '{password}': {e}")
            
            print("❌ No correct password found")
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    check_expert_password()
