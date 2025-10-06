"""Create Iran ports tables manually."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.__init__ import create_app
from backend.extensions import db
from backend.models import IranPort, PortProvinceMapping

def create_tables():
    """Create Iran ports tables."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Iran ports tables created successfully!")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'iran_port' in tables:
                print("✅ iran_port table exists")
            else:
                print("❌ iran_port table not found")
                
            if 'port_province_mapping' in tables:
                print("✅ port_province_mapping table exists")
            else:
                print("❌ port_province_mapping table not found")
                
        except Exception as e:
            print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()
