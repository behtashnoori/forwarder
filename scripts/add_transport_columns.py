#!/usr/bin/env python3
"""
Script to add missing transport method columns to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.wsgi import app
from backend.extensions import db
from sqlalchemy import text

def add_transport_columns():
    """Add missing transport method columns to shipment_request table."""
    
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'shipment_request' 
                AND column_name IN ('international_transport_method', 'domestic_transport_method', 'transport_method_preference')
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            print(f"Existing transport columns: {existing_columns}")
            
            # Add missing columns
            if 'international_transport_method' not in existing_columns:
                db.session.execute(text('ALTER TABLE shipment_request ADD COLUMN international_transport_method VARCHAR(32)'))
                print("✅ Added international_transport_method column")
            
            if 'domestic_transport_method' not in existing_columns:
                db.session.execute(text('ALTER TABLE shipment_request ADD COLUMN domestic_transport_method VARCHAR(32)'))
                print("✅ Added domestic_transport_method column")
            
            if 'transport_method_preference' not in existing_columns:
                db.session.execute(text('ALTER TABLE shipment_request ADD COLUMN transport_method_preference VARCHAR(32)'))
                print("✅ Added transport_method_preference column")
            
            db.session.commit()
            print("🎉 All transport method columns added successfully!")
            
            # Verify the columns exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'shipment_request' 
                AND column_name IN ('international_transport_method', 'domestic_transport_method', 'transport_method_preference')
            """))
            
            final_columns = [row[0] for row in result.fetchall()]
            print(f"Final transport columns: {final_columns}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding columns: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = add_transport_columns()
    sys.exit(0 if success else 1)
