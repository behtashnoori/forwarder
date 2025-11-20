#!/usr/bin/env python3

"""
Check Expert Password Directly
"""

import psycopg2
import bcrypt

def check_expert_password():
    """Check expert user password directly from database."""
    
    # Database connection parameters
    db_params = {
        'host': '127.0.0.1',
        'port': '5432',
        'database': 'forwarder_db',
        'user': 'postgres',
        'password': 'bagheri13'
    }
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL database")
        
        # Get expert1 user data
        cursor.execute("""
            SELECT id, username, password_hash, full_name, email, role 
            FROM expert_user 
            WHERE username = %s
        """, ('expert1',))
        
        user = cursor.fetchone()
        
        if not user:
            print("❌ Expert user 'expert1' not found!")
            return False
        
        user_id, username, password_hash, full_name, email, role = user
        
        print(f"✅ Found expert user:")
        print(f"   ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Full Name: {full_name}")
        print(f"   Email: {email}")
        print(f"   Role: {role}")
        print(f"   Password Hash: {password_hash[:50] if password_hash else 'NULL'}...")
        
        if not password_hash:
            print("❌ No password hash found!")
            return False
        
        # Test password verification
        test_passwords = ['expert123', 'password123', 'expert', 'test']
        
        for password in test_passwords:
            try:
                if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                    print(f"✅ Password '{password}' is CORRECT!")
                    return True
                else:
                    print(f"❌ Password '{password}' is incorrect")
            except Exception as e:
                print(f"❌ Error checking password '{password}': {e}")
        
        print("❌ No correct password found")
        return False
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    check_expert_password()
