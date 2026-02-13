#!/usr/bin/env python3
"""
Test Login Script
Tests login functionality for expert and admin users.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import bcrypt
from backend import create_app
from backend.models import ExpertUser
from backend.extensions import db
from backend.auth import auth_manager

def test_login(username: str, password: str) -> dict:
    """Test login with given credentials."""
    app = create_app()
    
    with app.app_context():
        try:
            # Use the auth manager to authenticate
            user_data = auth_manager.authenticate_user(username, password)
            
            if user_data:
                return {
                    'success': True,
                    'user': user_data
                }
            else:
                return {
                    'success': False,
                    'error': 'Authentication failed'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def check_user_exists(username: str) -> dict:
    """Check if user exists and return details."""
    app = create_app()
    
    with app.app_context():
        try:
            user = ExpertUser.query.filter_by(username=username).first()
            
            if not user:
                return {
                    'exists': False,
                    'message': f'User {username} does not exist'
                }
            
            return {
                'exists': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active,
                    'has_password_hash': bool(user.password_hash),
                    'password_hash_length': len(user.password_hash) if user.password_hash else 0
                }
            }
        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }

def verify_password(username: str, password: str) -> dict:
    """Verify password for a user."""
    app = create_app()
    
    with app.app_context():
        try:
            user = ExpertUser.query.filter_by(username=username).first()
            
            if not user:
                return {
                    'success': False,
                    'error': f'User {username} does not exist'
                }
            
            if not user.password_hash:
                return {
                    'success': False,
                    'error': 'User has no password hash'
                }
            
            # Verify password
            is_valid = bcrypt.checkpw(
                password.encode('utf-8'),
                user.password_hash.encode('utf-8')
            )
            
            return {
                'success': is_valid,
                'message': 'Password is valid' if is_valid else 'Password is invalid'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def fix_user_password(username: str, password: str) -> dict:
    """Fix/update user password."""
    app = create_app()
    
    with app.app_context():
        try:
            user = ExpertUser.query.filter_by(username=username).first()
            
            if not user:
                return {
                    'success': False,
                    'error': f'User {username} does not exist'
                }
            
            # Hash the new password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.password_hash = password_hash
            user.is_active = True
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Password updated for user {username}'
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

def main():
    """Main test function."""
    print("=" * 70)
    print("🧪 تست ورود کاربران (Expert و Admin)")
    print("=" * 70)
    
    # Test credentials
    test_users = [
        {
            'username': 'expert',
            'password': 'expert123',
            'role': 'expert',
            'description': 'کارشناس'
        },
        {
            'username': 'admin',
            'password': 'Pirooz13@!',
            'role': 'admin',
            'description': 'مدیر سیستم'
        }
    ]
    
    results = []
    
    for test_user in test_users:
        username = test_user['username']
        password = test_user['password']
        description = test_user['description']
        
        print(f"\n{'='*70}")
        print(f"📋 تست کاربر: {description} ({username})")
        print(f"{'='*70}")
        
        # Step 1: Check if user exists
        print(f"\n1️⃣ بررسی وجود کاربر...")
        user_check = check_user_exists(username)
        
        if not user_check.get('exists'):
            print(f"   ❌ کاربر {username} وجود ندارد!")
            print(f"   💡 در حال ایجاد کاربر...")
            
            # Try to create user
            app = create_app()
            with app.app_context():
                try:
                    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    new_user = ExpertUser(
                        username=username,
                        password_hash=password_hash,
                        full_name="کارشناس اول" if username == 'expert' else "مدیر سیستم",
                        email=f"{username}@company.com",
                        phone="09123456789",
                        role=test_user['role'],
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(new_user)
                    db.session.commit()
                    
                    print(f"   ✅ کاربر {username} ایجاد شد!")
                    user_check = check_user_exists(username)
                except Exception as e:
                    print(f"   ❌ خطا در ایجاد کاربر: {e}")
                    results.append({
                        'username': username,
                        'success': False,
                        'error': f'Failed to create user: {e}'
                    })
                    continue
        
        if user_check.get('exists'):
            user_info = user_check['user']
            print(f"   ✅ کاربر پیدا شد:")
            print(f"      - ID: {user_info['id']}")
            print(f"      - نام کامل: {user_info['full_name']}")
            print(f"      - نقش: {user_info['role']}")
            print(f"      - فعال: {user_info['is_active']}")
            print(f"      - رمز عبور: {'✅ دارد' if user_info['has_password_hash'] else '❌ ندارد'}")
            
            # Step 2: Verify password
            print(f"\n2️⃣ بررسی رمز عبور...")
            password_check = verify_password(username, password)
            
            if not password_check.get('success'):
                print(f"   ❌ رمز عبور معتبر نیست!")
                print(f"   💡 در حال اصلاح رمز عبور...")
                
                fix_result = fix_user_password(username, password)
                if fix_result.get('success'):
                    print(f"   ✅ رمز عبور اصلاح شد!")
                    password_check = verify_password(username, password)
                else:
                    print(f"   ❌ خطا در اصلاح رمز عبور: {fix_result.get('error')}")
            
            if password_check.get('success'):
                print(f"   ✅ رمز عبور معتبر است")
            else:
                print(f"   ❌ رمز عبور معتبر نیست: {password_check.get('error')}")
            
            # Step 3: Test login
            print(f"\n3️⃣ تست ورود...")
            login_result = test_login(username, password)
            
            if login_result.get('success'):
                user_data = login_result['user']
                print(f"   ✅ ورود موفق!")
                print(f"      - نام کاربری: {user_data['username']}")
                print(f"      - نام کامل: {user_data['full_name']}")
                print(f"      - نقش: {user_data['role']}")
                
                results.append({
                    'username': username,
                    'success': True,
                    'user': user_data
                })
            else:
                print(f"   ❌ ورود ناموفق!")
                print(f"      خطا: {login_result.get('error', 'Unknown error')}")
                
                # Try to fix
                print(f"   💡 در حال تلاش برای اصلاح...")
                fix_result = fix_user_password(username, password)
                
                if fix_result.get('success'):
                    print(f"   ✅ رمز عبور اصلاح شد، دوباره تست می‌کنیم...")
                    login_result = test_login(username, password)
                    
                    if login_result.get('success'):
                        print(f"   ✅ ورود موفق پس از اصلاح!")
                        results.append({
                            'username': username,
                            'success': True,
                            'user': login_result['user']
                        })
                    else:
                        print(f"   ❌ هنوز مشکل وجود دارد: {login_result.get('error')}")
                        results.append({
                            'username': username,
                            'success': False,
                            'error': login_result.get('error')
                        })
                else:
                    results.append({
                        'username': username,
                        'success': False,
                        'error': fix_result.get('error', 'Failed to fix password')
                    })
        else:
            results.append({
                'username': username,
                'success': False,
                'error': user_check.get('error', 'User does not exist')
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
        if not result.get('success'):
            print(f"      خطا: {result.get('error', 'Unknown error')}")
    
    print(f"\n📈 نتیجه کلی: {success_count}/{total_count} تست موفق")
    
    if success_count == total_count:
        print("✅ همه تست‌ها موفق بودند!")
        return 0
    else:
        print("❌ برخی تست‌ها ناموفق بودند!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
