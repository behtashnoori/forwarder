#!/usr/bin/env python3
"""
Add missing fields to expert_user table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app
from backend.extensions import db
from sqlalchemy import text

def add_expert_fields():
    """Add missing fields to expert_user table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if fields already exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'expert_user' 
                AND column_name IN ('manager_id', 'department', 'specialization')
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            # Add missing columns
            if 'manager_id' not in existing_columns:
                print("Adding manager_id column...")
                db.session.execute(text("""
                    ALTER TABLE expert_user 
                    ADD COLUMN manager_id BIGINT REFERENCES expert_user(id)
                """))
            
            if 'department' not in existing_columns:
                print("Adding department column...")
                db.session.execute(text("""
                    ALTER TABLE expert_user 
                    ADD COLUMN department VARCHAR(50)
                """))
            
            if 'specialization' not in existing_columns:
                print("Adding specialization column...")
                db.session.execute(text("""
                    ALTER TABLE expert_user 
                    ADD COLUMN specialization TEXT
                """))
            
            db.session.commit()
            print("✅ Expert user table updated successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating expert user table: {e}")
            return False
    
    return True

if __name__ == "__main__":
    add_expert_fields()
