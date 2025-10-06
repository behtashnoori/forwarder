"""Create Iran ports tables using raw SQL."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.__init__ import create_app
from backend.extensions import db

def create_tables_sql():
    """Create Iran ports tables using raw SQL."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create iran_port table
            db.session.execute(db.text("""
                CREATE TABLE IF NOT EXISTS iran_port (
                    id BIGSERIAL PRIMARY KEY,
                    name_fa VARCHAR(100) NOT NULL,
                    name_en VARCHAR(100) NOT NULL,
                    port_type VARCHAR(20) NOT NULL DEFAULT 'sea',
                    province_id BIGINT NOT NULL,
                    is_major_port BOOLEAN DEFAULT TRUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (province_id) REFERENCES province(id) ON DELETE CASCADE
                )
            """))
            
            # Create port_province_mapping table
            db.session.execute(db.text("""
                CREATE TABLE IF NOT EXISTS port_province_mapping (
                    id BIGSERIAL PRIMARY KEY,
                    port_id BIGINT NOT NULL,
                    province_id BIGINT NOT NULL,
                    suitability_score FLOAT DEFAULT 1.0,
                    transport_method VARCHAR(50),
                    estimated_days INTEGER,
                    is_recommended BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (port_id) REFERENCES iran_port(id) ON DELETE CASCADE,
                    FOREIGN KEY (province_id) REFERENCES province(id) ON DELETE CASCADE
                )
            """))
            
            # Add Iran entry point fields to shipment_request table
            db.session.execute(db.text("""
                ALTER TABLE shipment_request 
                ADD COLUMN IF NOT EXISTS iran_entry_port VARCHAR(100),
                ADD COLUMN IF NOT EXISTS iran_entry_province VARCHAR(100),
                ADD COLUMN IF NOT EXISTS iran_entry_port_id BIGINT,
                ADD COLUMN IF NOT EXISTS iran_entry_province_id BIGINT
            """))
            
            # Add foreign key constraints
            try:
                db.session.execute(db.text("""
                    ALTER TABLE shipment_request 
                    ADD CONSTRAINT fk_shipment_request_iran_entry_port_id 
                    FOREIGN KEY (iran_entry_port_id) REFERENCES iran_port(id) ON DELETE SET NULL
                """))
            except Exception as e:
                print(f"Foreign key constraint for port already exists or error: {e}")
            
            try:
                db.session.execute(db.text("""
                    ALTER TABLE shipment_request 
                    ADD CONSTRAINT fk_shipment_request_iran_entry_province_id 
                    FOREIGN KEY (iran_entry_province_id) REFERENCES province(id) ON DELETE SET NULL
                """))
            except Exception as e:
                print(f"Foreign key constraint for province already exists or error: {e}")
            
            db.session.commit()
            print("✅ Iran ports tables created successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables_sql()
