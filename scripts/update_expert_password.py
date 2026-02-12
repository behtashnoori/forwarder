#!/usr/bin/env python3

"""
Update Expert Password
"""

import psycopg2
import bcrypt

def update_expert_password():
    """Update expert user password."""
    
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
        
        # Hash the password
        password = "expert123"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        print(f"✅ Generated password hash for password: {password}")
        
        # Update expert1 password
        cursor.execute("""
            UPDATE expert_user 
            SET password_hash = %s 
            WHERE username = %s
        """, (password_hash, 'expert1'))
        
        rows_affected = cursor.rowcount
        conn.commit()
        
        if rows_affected > 0:
            print(f"✅ Updated password for expert1 user (affected {rows_affected} rows)")
            print(f"   Username: expert1")
            print(f"   Password: {password}")
        else:
            print("❌ No rows updated - user might not exist")
        
        # Also update other expert users
        expert_users = [
            ('expert2', 'expert123'),
            ('expert', 'expert123'),
            ('supervisor', 'admin123')
        ]
        
        for username, user_password in expert_users:
            user_password_hash = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                UPDATE expert_user 
                SET password_hash = %s 
                WHERE username = %s
            """, (user_password_hash, username))
            
            rows_affected = cursor.rowcount
            if rows_affected > 0:
                print(f"✅ Updated password for {username} (password: {user_password})")
        
        conn.commit()
        print("✅ All passwords updated successfully!")
        
        return True
        
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
    update_expert_password()
