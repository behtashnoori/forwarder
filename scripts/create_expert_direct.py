#!/usr/bin/env python3

"""
Create Expert User Direct SQL Script
"""

import sqlite3
import bcrypt
from datetime import datetime
import os

def create_expert_user():
    """Create a test expert user using direct SQL."""
    
    # Find the database file
    db_paths = [
        'instance/app.db',
        'backend/instance/app.db',
        'app.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found!")
        print("Searched paths:", db_paths)
        return False
    
    print(f"✅ Found database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if expert_user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expert_user'")
        if not cursor.fetchone():
            print("❌ expert_user table does not exist!")
            return False
        
        # Check if expert1 already exists
        cursor.execute("SELECT id, username FROM expert_user WHERE username = ?", ('expert1',))
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'expert1',
            password_hash,
            'کارشناس تست',
            'expert1@test.com',
            '09123456789',
            'expert',
            1,  # is_active = True
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        print("✅ Expert user 'expert1' created successfully!")
        print(f"   ID: {user_id}")
        print(f"   Username: expert1")
        print(f"   Password: {password}")
        print(f"   Full Name: کارشناس تست")
        print(f"   Email: expert1@test.com")
        print(f"   Role: expert")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating expert user: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_expert_user()
