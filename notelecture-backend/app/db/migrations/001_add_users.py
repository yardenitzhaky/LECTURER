#!/usr/bin/env python3
"""
Database migration script to add user authentication support.
This script:
1. Creates the users table for FastAPI-Users
2. Adds user_id column to lectures table
3. Creates a default user for existing lectures (optional)
"""

import os
import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from app.core.config import settings
from app.db.models import User, Lecture
from app.db.base_class import Base
from app.utils.database import check_column_exists
from app.utils.auth import get_password_hash, generate_uuid

def create_tables(engine):
    """Create all tables defined in models"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")

def add_user_id_to_lectures(engine):
    """Add user_id column to lectures table if it doesn't exist"""
    print("Checking if user_id column exists in lectures table...")
    
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        column_exists = check_column_exists(db, 'lectures', 'user_id')
        
        if not column_exists:
            print("Adding user_id column to lectures table...")
            # Add the column as nullable first
            db.execute(text("""
                ALTER TABLE lectures 
                ADD COLUMN user_id VARCHAR(36) NULL
            """))
            
            # Add foreign key constraint
            db.execute(text("""
                ALTER TABLE lectures 
                ADD CONSTRAINT fk_lecture_user 
                FOREIGN KEY (user_id) REFERENCES users(id)
            """))
            
            # Add index for performance
            db.execute(text("""
                CREATE INDEX idx_lecture_user_id ON lectures(user_id)
            """))
            
            db.commit()
            print("✅ user_id column added to lectures table")
        else:
            print("✅ user_id column already exists in lectures table")
            
    except Exception as e:
        print(f"❌ Error adding user_id column: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_default_user_for_existing_lectures(engine):
    """Create a default user and assign existing lectures to them"""
    print("Checking for existing lectures without user assignment...")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if there are any lectures without user_id
        lectures_without_user = db.query(Lecture).filter(Lecture.user_id.is_(None)).count()
        
        if lectures_without_user > 0:
            print(f"Found {lectures_without_user} lectures without user assignment")
            
            # Create a default user
            default_user_id = generate_uuid()
            default_user = User(
                id=default_user_id,
                email="admin@notelecture.ai",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True,
                is_verified=True,
                first_name="Default",
                last_name="User"
            )
            
            # Check if default user already exists
            existing_user = db.query(User).filter(User.email == "admin@notelecture.ai").first()
            if not existing_user:
                db.add(default_user)
                db.flush()
                print(f"✅ Created default user with ID: {default_user_id}")
                user_id_to_use = default_user_id
            else:
                print(f"✅ Using existing default user with ID: {existing_user.id}")
                user_id_to_use = str(existing_user.id)
            
            # Assign all unassigned lectures to the default user
            db.query(Lecture).filter(Lecture.user_id.is_(None)).update(
                {Lecture.user_id: user_id_to_use}
            )
            
            db.commit()
            print(f"✅ Assigned {lectures_without_user} lectures to default user")
        else:
            print("✅ All lectures already have user assignments")
            
    except Exception as e:
        print(f"❌ Error creating default user: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    print("🚀 Starting database migration for user authentication...")
    print(f"Database URL: {settings.DATABASE_URL[:50]}...")
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # Step 1: Create all tables (including users table)
        create_tables(engine)
        
        # Step 2: Add user_id column to lectures table
        add_user_id_to_lectures(engine)
        
        # Step 3: Create default user for existing lectures
        create_default_user_for_existing_lectures(engine)
        
        print("\n🎉 Database migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your .env file with Google OAuth credentials")
        print("2. Install new backend dependencies: pip install -r requirements.txt")
        print("3. Install new frontend dependencies: npm install")
        print("4. Start the application")
        
        print("\nDefault admin user created:")
        print("  Email: admin@notelecture.ai")
        print("  Password: admin123")
        print("  (Please change this password after first login)")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()