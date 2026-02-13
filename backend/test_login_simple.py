#!/usr/bin/env python3
"""
Simple Login Test Script
Tests login functionality by checking database directly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from datetime import datetime
    import bcrypt
    from backend import create_app
    from backend.models import ExpertUser
    from backend.extensions import db
    from backend.auth import auth_manager
    
    def main():
        """Main test function."""
        print("=" * 70)
        print("🧪 تست ورود کاربران (Expert و Admin)")
        print("=" * 70)
        
        app = create_app()
        
        with app.app_context():
            # Test credentials
            test_users = [
                {'username': 'expert', 'password': 'expert123', 'role': 'expert', 'desc': 'کارشناس'},
                {'username': 'admin', 'password': 'Pirooz13@!', 'role': 'admin', 'desc': 'مدیر سیستم'}
            ]
            
            results = []
            
            for test_user in test_users:
                username = test_user['username']
                password = test_user['password']
                desc = test_user['desc']
                
                print(f"\n{'='*70}")
                print(f"📋 تست کاربر: {desc} ({username})")
                print(f"{'='*70}")
                
                # Check if user exists
                user = ExpertUser.query.filter_by(username=username).first()
                
                if not user:
                    print(f"   ❌ کاربر {username} وجود ندارد!")
                    print(f"   💡 در حال ایجاد کاربر...")
                    
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
                        user = new_user
                    except Exception as e:
                        print(f"   ❌ خطا در ایجاد کاربر: {e}")
                        results.append({'username': username, 'success': False, 'error': str(e)})
                        continue
                
                if user:
                    print(f"   ✅ کاربر پیدا شد:")
                    print(f"      - ID: {user.id}")
                    print(f"      - نام کامل: {user.full_name}")
                    print(f"      - نقش: {user.role}")
                    print(f"      - فعال: {user.is_active}")
                    
                    # Verify password
                    if not user.password_hash:
                        print(f"   ❌ رمز عبور ندارد!")
                        print(f"   💡 در حال تنظیم رمز عبور...")
                        try:
                            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            user.password_hash = password_hash
                            user.is_active = True
                            db.session.commit()
                            print(f"   ✅ رمز عبور تنظیم شد!")
                        except Exception as e:
                            print(f"   ❌ خطا در تنظیم رمز عبور: {e}")
                            results.append({'username': username, 'success': False, 'error': str(e)})
                            continue
                    
                    # Test password verification
                    try:
                        is_valid = bcrypt.checkpw(
                            password.encode('utf-8'),
                            user.password_hash.encode('utf-8')
                        )
                        
                        if not is_valid:
                            print(f"   ❌ رمز عبور معتبر نیست!")
                            print(f"   💡 در حال اصلاح رمز عبور...")
                            
                            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            user.password_hash = password_hash
                            user.is_active = True
                            db.session.commit()
                            
                            # Verify again
                            is_valid = bcrypt.checkpw(
                                password.encode('utf-8'),
                                user.password_hash.encode('utf-8')
                            )
                            
                            if is_valid:
                                print(f"   ✅ رمز عبور اصلاح شد!")
                            else:
                                print(f"   ❌ هنوز مشکل وجود دارد!")
                                results.append({'username': username, 'success': False, 'error': 'Password fix failed'})
                                continue
                        else:
                            print(f"   ✅ رمز عبور معتبر است")
                    except Exception as e:
                        print(f"   ❌ خطا در بررسی رمز عبور: {e}")
                        results.append({'username': username, 'success': False, 'error': str(e)})
                        continue
                    
                    # Test login using auth_manager
                    print(f"\n   🔐 تست ورود...")
                    try:
                        user_data = auth_manager.authenticate_user(username, password)
                        
                        if user_data:
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
                            results.append({
                                'username': username,
                                'success': False,
                                'error': 'Authentication failed'
                            })
                    except Exception as e:
                        print(f"   ❌ خطا در تست ورود: {e}")
                        import traceback
                        traceback.print_exc()
                        results.append({
                            'username': username,
                            'success': False,
                            'error': str(e)
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
        
except ImportError as e:
    print(f"❌ خطا در import: {e}")
    print("\n💡 لطفاً dependencies را نصب کنید:")
    print("   pip install -r backend/requirements.txt")
    print("   یا")
    print("   py -m pip install -r backend/requirements.txt")
    sys.exit(1)
