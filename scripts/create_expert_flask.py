#!/usr/bin/env python3

"""
Create Expert User using Flask App Context
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import bcrypt
from backend import create_app
from backend.extensions import db

def create_expert_user():
    """Create a test expert user using Flask app context."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if expert1 already exists
            from backend.models import ExpertUser
            
            existing_user = ExpertUser.query.filter_by(username='expert1').first()
            if existing_user:
                print("✅ Expert user 'expert1' already exists!")
                print(f"   ID: {existing_user.id}")
                print(f"   Username: {existing_user.username}")
                print(f"   Full Name: {existing_user.full_name}")
                print(f"   Email: {existing_user.email}")
                print(f"   Role: {existing_user.role}")
                print(f"   Active: {existing_user.is_active}")
                return existing_user
            
            # Hash the password
            password = "expert123"
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Create new expert user
            expert = ExpertUser(
                username='expert1',
                password_hash=password_hash,
                full_name='کارشناس تست',
                email='expert1@test.com',
                phone='09123456789',
                role='expert',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(expert)
            db.session.commit()
            
            print("✅ Expert user 'expert1' created successfully!")
            print(f"   ID: {expert.id}")
            print(f"   Username: {expert.username}")
            print(f"   Password: {password}")
            print(f"   Full Name: {expert.full_name}")
            print(f"   Email: {expert.email}")
            print(f"   Role: {expert.role}")
            
            return expert
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating expert user: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == '__main__':
    create_expert_user()
