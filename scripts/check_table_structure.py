#!/usr/bin/env python3

"""
Check Table Structure
"""

import psycopg2

def check_table_structure():
    """Check the structure of expert_user table."""
    
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
        
        # Get table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'expert_user' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        if not columns:
            print("❌ expert_user table does not exist!")
            return False
        
        print("✅ expert_user table structure:")
        print("   Column Name          | Data Type         | Nullable | Default")
        print("   " + "-" * 70)
        for col in columns:
            col_name = col[0]
            data_type = col[1]
            nullable = "YES" if col[2] == "YES" else "NO"
            default = col[3] or ""
            print(f"   {col_name:<20} | {data_type:<16} | {nullable:<8} | {default}")
        
        # Get sample data
        cursor.execute("SELECT id, username, full_name, role FROM expert_user LIMIT 5;")
        users = cursor.fetchall()
        
        if users:
            print(f"\n✅ Sample users ({len(users)} found):")
            for user in users:
                print(f"   ID: {user[0]}, Username: {user[1]}, Name: {user[2]}, Role: {user[3]}")
        else:
            print("\n❌ No users found in expert_user table")
        
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
    check_table_structure()
