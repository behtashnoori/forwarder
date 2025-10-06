"""Script to run database migrations for CRM hierarchy system."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask_migrate import upgrade, init, migrate, current, history
from __init__ import create_app
from extensions import db

def run_migrations():
    """Run database migrations."""
    app = create_app()
    
    with app.app_context():
        try:
            migration_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            
            # Check current migration status
            print("Checking current migration status...")
            try:
                current_revision = current(directory=migration_dir)
                print(f"Current revision: {current_revision}")
            except Exception as e:
                print(f"No current revision found: {e}")
                print("Initializing migrations...")
                init(directory=migration_dir)
            
            # Show migration history
            print("\nMigration history:")
            for revision in history(directory=migration_dir):
                print(f"  {revision.revision}: {revision.doc}")
            
            # Run migrations
            print("\nRunning migrations...")
            upgrade(directory=migration_dir)
            
            print("✅ Migrations completed successfully!")
            
            # Verify tables exist
            print("\nVerifying tables...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'expert_user', 'transport_method', 'expert_specialization',
                'assignment_rule', 'assignment_log', 'shipment_request'
            ]
            
            for table in required_tables:
                if table in tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} - MISSING")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = run_migrations()
    if success:
        print("\n🎉 Database setup completed successfully!")
        print("You can now run the seed script to populate initial data.")
    else:
        print("\n💥 Database setup failed!")
        sys.exit(1)
