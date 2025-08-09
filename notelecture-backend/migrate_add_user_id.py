#!/usr/bin/env python3
"""
Migration script to add user_id column to lectures table
"""
import logging
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
sys.path.insert(0, project_root)

try:
    from app.core.config import settings
except ImportError as e:
    logging.error(f"Failed to import settings: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)-8s - %(message)s")
logger = logging.getLogger(__name__)

def migrate_add_user_id():
    """Add user_id column to lectures table if it doesn't exist"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            # Check if user_id column exists
            result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'lectures' 
                AND COLUMN_NAME = 'user_id'
            """))
            
            column_exists = result.scalar() > 0
            
            if column_exists:
                logger.info("user_id column already exists in lectures table")
                return
            
            logger.info("Adding user_id column to lectures table...")
            
            # Add the user_id column
            connection.execute(text("""
                ALTER TABLE lectures 
                ADD COLUMN user_id VARCHAR(36) NOT NULL DEFAULT ''
            """))
            
            # Add foreign key constraint
            connection.execute(text("""
                ALTER TABLE lectures 
                ADD CONSTRAINT fk_lectures_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id)
            """))
            
            # Add index
            connection.execute(text("""
                CREATE INDEX ix_lectures_user_id ON lectures(user_id)
            """))
            
            connection.commit()
            logger.info("Successfully added user_id column with foreign key constraint and index")
            
    except OperationalError as e:
        logger.error(f"Database operation failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_add_user_id()