#!/usr/bin/env python3
"""
Database Setup Script

Creates all database tables based on existing SQLAlchemy models.
Run this script once on a new server to initialize the database.

Usage:
    python setup_database.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string (default: postgresql://postgres:postgres@localhost:5432/goec)
"""
import sys
import os


def main():
    """Setup database tables."""
    print("=" * 60)
    print("Database Setup for GOEC Analytics")
    print("=" * 60)
    
    # Import after sys.path is set
    from database.connection import init_db, DATABASE_URL, engine
    
    print(f"\nDatabase URL: {DATABASE_URL.split('@')[-1]}")  # Hide credentials
    print(f"\nCreating tables based on SQLAlchemy models...")
    print("-" * 60)
    
    try:
        # Initialize database (creates all tables)
        init_db()
        
        # List created tables
        print("\nVerifying tables...")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if tables:
            print(f"\n✓ Successfully created {len(tables)} tables:")
            for table in sorted(tables):
                print(f"  - {table}")
        else:
            print("\n⚠ Warning: No tables found")
            
        print("\n" + "=" * 60)
        print("Database setup completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during database setup:")
        print(f"  {str(e)}")
        print("\nPlease ensure:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'goec' exists")
        print("  3. Connection credentials are correct")
        print("  4. DATABASE_URL environment variable is set (if using custom connection)")
        sys.exit(1)


if __name__ == "__main__":
    main()
