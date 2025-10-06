"""Complete setup script for CRM hierarchy system."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_migrations import run_migrations
from seed_crm_hierarchy import seed_crm_hierarchy

def setup_crm_hierarchy():
    """Complete setup of CRM hierarchy system."""
    print("🚀 Setting up CRM Hierarchy System...")
    print("=" * 50)
    
    # Step 1: Run migrations
    print("\n📊 Step 1: Running database migrations...")
    if not run_migrations():
        print("❌ Migration failed. Aborting setup.")
        return False
    
    # Step 2: Seed initial data
    print("\n🌱 Step 2: Seeding initial data...")
    try:
        seed_crm_hierarchy()
        print("✅ Initial data seeded successfully!")
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        return False
    
    # Step 3: Verify setup
    print("\n🔍 Step 3: Verifying setup...")
    try:
        from __init__ import create_app
        from models import ExpertUser, TransportMethod, ExpertSpecialization, AssignmentRule
        
        app = create_app()
        with app.app_context():
            # Check if data was created
            user_count = ExpertUser.query.count()
            transport_count = TransportMethod.query.count()
            spec_count = ExpertSpecialization.query.count()
            rule_count = AssignmentRule.query.count()
            
            print(f"  👥 Users created: {user_count}")
            print(f"  🚛 Transport methods: {transport_count}")
            print(f"  🎯 Specializations: {spec_count}")
            print(f"  ⚙️  Assignment rules: {rule_count}")
            
            if user_count > 0 and transport_count > 0:
                print("✅ Setup verification passed!")
            else:
                print("⚠️  Setup verification failed - some data missing")
                return False
                
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 CRM Hierarchy System setup completed successfully!")
    print("\n📋 What was created:")
    print("  • Database tables for hierarchy system")
    print("  • Transport methods (road, rail, air, sea, express)")
    print("  • CRM Manager user (username: crm_manager, password: crm123)")
    print("  • Business Expert users (username: business_expert1-3, password: business123)")
    print("  • Assignment rules for automatic request routing")
    print("  • User specializations in transport methods")
    
    print("\n🔑 Login credentials:")
    print("  CRM Manager: crm_manager / crm123")
    print("  Business Expert 1: business_expert1 / business123")
    print("  Business Expert 2: business_expert2 / business123")
    print("  Business Expert 3: business_expert3 / business123")
    
    print("\n🌐 Access URLs:")
    print("  • User Management: http://localhost:5173/user-management")
    print("  • CRM Dashboard: http://localhost:5173/crm")
    print("  • Expert Console: http://localhost:5173/expert")
    
    return True

if __name__ == "__main__":
    success = setup_crm_hierarchy()
    if not success:
        print("\n💥 Setup failed!")
        sys.exit(1)
