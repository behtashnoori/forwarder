#!/usr/bin/env python3

"""
Create Expert User using PostgreSQL
"""

import psycopg2
import bcrypt
from datetime import datetime
import os

def create_expert_user():
    """Create a test expert user using direct PostgreSQL connection."""
    
    # Database connection parameters
    db_params = {
        'host': '127.0.0.1',
        'port': '5432',
        'database': 'forwarder_db',
        'user': 'postgres',
        'password': 'change_me'
    }
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL database")
        
        # Check if expert_user table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'expert_user'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("❌ expert_user table does not exist!")
            print("   Please run migrations first")
            return False
        
        print("✅ expert_user table exists")
        
        # Check if expert1 already exists
        cursor.execute("SELECT id, username FROM expert_user WHERE username = %s", ('expert1',))
        existing = cursor.fetchone()
        
        if existing:
            print(f"✅ Expert user 'expert1' already exists! (ID: {existing[0]})")
            return True
        
        # Hash the password
        password = "expert123"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create expert user
        cursor.execute("""
            INSERT INTO expert_user (
                username, password_hash, full_name, email, phone, role, 
                is_active, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            'expert1',
            password_hash,
            'کارشناس تست',
            'expert1@test.com',
            '09123456789',
            'expert',
            True,  # is_active
            datetime.utcnow()
        ))
        
        user_id = cursor.fetchone()[0]
        conn.commit()
        
        print("✅ Expert user 'expert1' created successfully!")
        print(f"   ID: {user_id}")
        print(f"   Username: expert1")
        print(f"   Password: {password}")
        print(f"   Full Name: کارشناس تست")
        print(f"   Email: expert1@test.com")
        print(f"   Role: expert")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error creating expert user: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    create_expert_user()
