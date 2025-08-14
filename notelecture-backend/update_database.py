#!/usr/bin/env python3
"""
Update database schema and initialize subscription plans.
Run this to add the new subscription tables and data.
"""

from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.db.models import Base, SubscriptionPlan, User

def update_database():
    """Update database schema and initialize data"""
    print("Updating database schema...")
    
    # Create all tables (including new ones)
    Base.metadata.create_all(bind=engine)
    print("Database schema updated")
    
    session = SessionLocal()
    
    try:
        # Check if free_lectures_used column exists in users table
        result = session.execute(text("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'free_lectures_used'
        """))
        
        if result.scalar() == 0:
            print("Adding free_lectures_used column to users table...")
            session.execute(text("ALTER TABLE users ADD COLUMN free_lectures_used INTEGER DEFAULT 0"))
            session.commit()
            print("Added free_lectures_used column")
        else:
            print("free_lectures_used column already exists")
        
        # Check if subscription plans exist
        existing_plans = session.query(SubscriptionPlan).count()
        if existing_plans == 0:
            print("Creating subscription plans...")
            
            plans = [
                SubscriptionPlan(
                    name="Weekly",
                    duration_days=7,
                    price=1.90,
                    lecture_limit=10
                ),
                SubscriptionPlan(
                    name="Monthly", 
                    duration_days=30,
                    price=5.90,
                    lecture_limit=50
                ),
                SubscriptionPlan(
                    name="6 Months",
                    duration_days=180,
                    price=14.90,
                    lecture_limit=300
                ),
                SubscriptionPlan(
                    name="12 Months",
                    duration_days=365, 
                    price=24.90,
                    lecture_limit=750
                )
            ]
            
            for plan in plans:
                session.add(plan)
            
            session.commit()
            print(f"Created {len(plans)} subscription plans")
        else:
            print(f"Subscription plans already exist ({existing_plans} plans found)")
            
        print("Database update completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Error during database update: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    update_database()