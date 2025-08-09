#!/usr/bin/env python3
"""
Database migration script to add the 'notes' column to the lectures table.
Run this script to update existing databases.
"""

import os
from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate_database():
    """Add notes column to lectures table if it doesn't exist"""
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check if notes column already exists
            result = connection.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'lectures' 
                AND COLUMN_NAME = 'notes'
            """))
            
            if result.fetchone() is None:
                # Column doesn't exist, add it
                print("Adding 'notes' column to lectures table...")
                connection.execute(text("""
                    ALTER TABLE lectures ADD COLUMN notes TEXT NULL
                """))
                connection.commit()
                print("✅ Successfully added 'notes' column to lectures table")
            else:
                print("✅ 'notes' column already exists in lectures table")
                
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("Starting database migration...")
    migrate_database()
    print("Migration completed!")