#!/usr/bin/env python3
"""
Migration script to add the Payment table for PayPal integration.
Run this script after updating the models to ensure the Payment table is created.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.core.config import settings
from app.db.models import Base, Payment

def run_migration():
    """Create the Payment table if it doesn't exist."""
    try:
        # Create database engine
        engine = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''))
        
        # Create all tables (this will only create missing tables)
        Base.metadata.create_all(bind=engine)
        
        print("✅ Payment table migration completed successfully!")
        print("The following table was created/verified:")
        print("- payments")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()