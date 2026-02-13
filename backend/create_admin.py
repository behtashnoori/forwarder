#!/usr/bin/env python3
"""
Create Admin User Script
Creates an admin user with specified credentials.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import bcrypt
from backend import create_app
from backend.models import ExpertUser
from backend.extensions import db

def create_admin_user():
    """Create admin user with specified credentials."""
    app = create_app()
    
    with app.app_context():
        try:
            username = "admin"
            password = "Pirooz13@!"
            
            # Check if admin user already exists
            existing_user = ExpertUser.query.filter_by(username=username).first()
            if existing_user:
                print(f"⚠️  کاربر admin از قبل وجود دارد!")
                print(f"   ID: {existing_user.id}")
                print(f"   Username: {existing_user.username}")
                print(f"   Full Name: {existing_user.full_name}")
                print(f"   Role: {existing_user.role}")
                print(f"   Active: {existing_user.is_active}")
                
                # Automatically update password and ensure correct settings
                print(f"\n💡 در حال به‌روزرسانی رمز عبور و تنظیمات...")
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                existing_user.password_hash = password_hash
                existing_user.role = 'admin'  # Ensure role is admin
                existing_user.is_active = True
                existing_user.full_name = "مدیر سیستم"  # Ensure correct full name
                if not existing_user.email:
                    existing_user.email = "admin@company.com"
                if not existing_user.phone:
                    existing_user.phone = "09120000000"
                db.session.commit()
                print("✅ رمز عبور و تنظیمات کاربر admin به‌روزرسانی شد!")
                print(f"   Username: {username}")
                print(f"   Password: {password}")
                return existing_user
            
            # Hash the password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Create new admin user
            admin = ExpertUser(
                username=username,
                password_hash=password_hash,
                full_name="مدیر سیستم",
                email="admin@company.com",
                phone="09120000000",
                role="admin",
                department="management",
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ کاربر admin با موفقیت ایجاد شد!")
            print(f"   ID: {admin.id}")
            print(f"   Username: {admin.username}")
            print(f"   Password: {password}")
            print(f"   Full Name: {admin.full_name}")
            print(f"   Role: {admin.role}")
            print(f"   Active: {admin.is_active}")
            print("\n🔑 می‌توانید با این اطلاعات وارد سیستم شوید:")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            
            return admin
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطا در ایجاد کاربر admin: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 ایجاد کاربر Admin")
    print("=" * 60)
    create_admin_user()
    print("=" * 60)
