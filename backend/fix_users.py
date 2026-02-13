#!/usr/bin/env python3
"""
Fix Users Script
Creates or fixes admin and expert users with correct passwords.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import bcrypt
from backend import create_app
from backend.models import ExpertUser
from backend.extensions import db

def create_or_fix_user(username, password, full_name, email, phone, role):
    """Create or fix a user with the given credentials."""
    app = create_app()
    
    with app.app_context():
        try:
            user = ExpertUser.query.filter_by(username=username).first()
            
            if user:
                # User exists, update password and ensure active
                print(f"   🔧 کاربر {username} پیدا شد، در حال به‌روزرسانی...")
                
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user.password_hash = password_hash
                user.is_active = True
                user.role = role
                user.full_name = full_name
                if email:
                    user.email = email
                if phone:
                    user.phone = phone
                
                db.session.commit()
                
                print(f"   ✅ کاربر {username} به‌روزرسانی شد!")
                return user
            else:
                # User doesn't exist, create it
                print(f"   ➕ ایجاد کاربر جدید {username}...")
                
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                new_user = ExpertUser(
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    role=role,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(new_user)
                db.session.commit()
                
                print(f"   ✅ کاربر {username} ایجاد شد!")
                return new_user
                
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ خطا: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    """Main function."""
    print("=" * 70)
    print("🔧 ایجاد/اصلاح کاربران Expert و Admin")
    print("=" * 70)
    
    users_to_create = [
        {
            'username': 'expert',
            'password': 'expert123',
            'full_name': 'کارشناس اول',
            'email': 'expert@company.com',
            'phone': '09123456789',
            'role': 'expert'
        },
        {
            'username': 'admin',
            'password': 'Pirooz13@!',
            'full_name': 'مدیر سیستم',
            'email': 'admin@company.com',
            'phone': '09120000000',
            'role': 'admin'
        }
    ]
    
    results = []
    
    for user_data in users_to_create:
        print(f"\n{'='*70}")
        print(f"📋 پردازش کاربر: {user_data['username']} ({user_data['role']})")
        print(f"{'='*70}")
        
        user = create_or_fix_user(
            username=user_data['username'],
            password=user_data['password'],
            full_name=user_data['full_name'],
            email=user_data['email'],
            phone=user_data['phone'],
            role=user_data['role']
        )
        
        if user:
            results.append({
                'username': user_data['username'],
                'success': True,
                'user': user
            })
            
            # Verify password
            try:
                is_valid = bcrypt.checkpw(
                    user_data['password'].encode('utf-8'),
                    user.password_hash.encode('utf-8')
                )
                if is_valid:
                    print(f"   ✅ رمز عبور معتبر است")
                else:
                    print(f"   ⚠️  رمز عبور معتبر نیست!")
            except Exception as e:
                print(f"   ⚠️  خطا در بررسی رمز عبور: {e}")
        else:
            results.append({
                'username': user_data['username'],
                'success': False
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 خلاصه نتایج")
    print(f"{'='*70}")
    
    success_count = sum(1 for r in results if r.get('success'))
    total_count = len(results)
    
    for result in results:
        status = "✅ موفق" if result.get('success') else "❌ ناموفق"
        print(f"   {status} - {result['username']}")
    
    print(f"\n📈 نتیجه کلی: {success_count}/{total_count} کاربر آماده")
    
    if success_count == total_count:
        print("\n✅ همه کاربران آماده هستند!")
        print("\n🔑 اطلاعات ورود:")
        for user_data in users_to_create:
            print(f"   - {user_data['username']}: {user_data['password']}")
        return 0
    else:
        print("\n❌ برخی کاربران ایجاد نشدند!")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except ImportError as e:
        print(f"❌ خطا در import: {e}")
        print("\n💡 لطفاً dependencies را نصب کنید:")
        print("   pip install -r backend/requirements.txt")
        print("   یا")
        print("   py -m pip install -r backend/requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
