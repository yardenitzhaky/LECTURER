#!/usr/bin/env python3
"""
Comprehensive database migration script for NoteLecture.AI
This script handles all database setup and migrations:
1. Creates database if it doesn't exist
2. Creates all tables from current models
3. Handles any schema updates for existing databases
"""

import os
import sys
import uuid
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

try:
    from app.core.config import settings
    from app.db.models import User, Lecture, SubscriptionPlan, Base
    from app.utils.database import check_column_exists
    from app.utils.common import get_password_hash, generate_uuid
except ImportError as e:
    print(f"❌ Failed to import application modules: {e}")
    print(f"Ensure you're running from the project root: {project_root}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)-8s - %(message)s")
logger = logging.getLogger(__name__)


def create_database_if_not_exists(database_url: str):
    """Create the database if it doesn't exist."""
    from sqlalchemy.engine.url import make_url, URL
    
    try:
        url = make_url(database_url)
    except Exception as e:
        logger.error(f"Invalid DATABASE_URL format: {e}")
        sys.exit(1)

    db_name = url.database
    if not db_name:
        logger.error("DATABASE_URL must specify a database name")
        sys.exit(1)

    # Create server connection URL (without database)
    server_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=None
    )

    logger.info(f"Creating database '{db_name}' if it doesn't exist...")
    
    try:
        temp_engine = create_engine(server_url, pool_size=2, max_overflow=0)
        with temp_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
            connection.execute(text("COMMIT;"))
        logger.info(f"✅ Database '{db_name}' ready")
    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Database creation failed: {e}")
        if "Access denied" in str(e):
            logger.error("User needs CREATE DATABASE privileges")
        sys.exit(1)
    finally:
        if 'temp_engine' in locals():
            temp_engine.dispose()


def create_tables(engine):
    """Create all tables defined in models."""
    logger.info("Creating/updating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created/updated successfully")
    except Exception as e:
        logger.error(f"Table creation failed: {e}")
        raise


def migrate_existing_data(engine):
    """Handle migrations for existing databases."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if we need to add user_id column to lectures
        if not check_column_exists(db, 'lectures', 'user_id'):
            logger.info("Adding user_id column to lectures table...")
            db.execute(text("ALTER TABLE lectures ADD COLUMN user_id VARCHAR(36) NULL"))
            db.execute(text("""
                ALTER TABLE lectures 
                ADD CONSTRAINT fk_lecture_user 
                FOREIGN KEY (user_id) REFERENCES users(id)
            """))
            db.execute(text("CREATE INDEX idx_lecture_user_id ON lectures(user_id)"))
            db.commit()
            logger.info("✅ user_id column added")
        
        # Check if we need to add notes column to lectures
        if not check_column_exists(db, 'lectures', 'notes'):
            logger.info("Adding notes column to lectures table...")
            db.execute(text("ALTER TABLE lectures ADD COLUMN notes TEXT NULL"))
            db.commit()
            logger.info("✅ notes column added")
        
        # Create default user for any lectures without user_id
        lectures_without_user = db.query(Lecture).filter(Lecture.user_id.is_(None)).count()
        
        if lectures_without_user > 0:
            logger.info(f"Found {lectures_without_user} lectures without user assignment")
            
            # Check for existing default user
            existing_user = db.query(User).filter(User.email == "admin@notelecture.ai").first()
            
            if not existing_user:
                # Create default admin user
                default_user_id = generate_uuid()
                default_user = User(
                    id=default_user_id,
                    email="admin@notelecture.ai",
                    hashed_password=get_password_hash("admin123"),
                    is_active=True,
                    is_superuser=True,
                    is_verified=True,
                    first_name="Admin",
                    last_name="User"
                )
                db.add(default_user)
                db.flush()
                user_id_to_use = default_user_id
                logger.info(f"✅ Created default admin user")
            else:
                user_id_to_use = str(existing_user.id)
                logger.info("✅ Using existing admin user")
            
            # Assign unassigned lectures to admin user
            db.query(Lecture).filter(Lecture.user_id.is_(None)).update(
                {Lecture.user_id: user_id_to_use}
            )
            db.commit()
            logger.info(f"✅ Assigned {lectures_without_user} lectures to admin user")
        
        # Check if free_lectures_used column exists in users table
        if not check_column_exists(db, 'users', 'free_lectures_used'):
            logger.info("Adding free_lectures_used column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN free_lectures_used INTEGER DEFAULT 0"))
            db.commit()
            logger.info("✅ free_lectures_used column added")
        
        # Initialize subscription plans if they don't exist
        existing_plans = db.query(SubscriptionPlan).count()
        if existing_plans == 0:
            logger.info("Creating subscription plans...")
            
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
                db.add(plan)
            
            db.commit()
            logger.info(f"✅ Created {len(plans)} subscription plans")
        else:
            logger.info(f"✅ Subscription plans already exist ({existing_plans} plans found)")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_subscription_plans_standalone():
    """Initialize default subscription plans as a standalone function"""
    from app.db.connection import SessionLocal
    
    session = SessionLocal()
    
    try:
        # Check if plans already exist
        existing_plans = session.query(SubscriptionPlan).count()
        if existing_plans > 0:
            logger.info(f"Subscription plans already exist ({existing_plans} plans found)")
            return
        
        # Create default subscription plans
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
        logger.info(f"✅ Created {len(plans)} subscription plans")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during subscription plan initialization: {e}")
        raise
    finally:
        session.close()


def main():
    """Main migration function."""
    print("🚀 Starting NoteLecture.AI database migration...")
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'localhost'}")
    
    try:
        # Step 1: Ensure database exists
        create_database_if_not_exists(settings.DATABASE_URL)
        
        # Step 2: Create engine for main database
        engine = create_engine(settings.DATABASE_URL)
        
        # Step 3: Create/update tables
        create_tables(engine)
        
        # Step 4: Handle data migrations
        migrate_existing_data(engine)
        
        print("\n🎉 Database migration completed successfully!")
        print("\n📋 Summary:")
        print("  ✅ Database created/verified")
        print("  ✅ All tables created/updated")
        print("  ✅ Data migrations applied")
        print("  ✅ Subscription plans initialized")
        print("\n🔐 Default admin credentials:")
        print("  Email: admin@notelecture.ai")
        print("  Password: admin123")
        print("  (Change this password after first login)")
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "plans":
        # Run just subscription plan initialization
        print("🔧 Initializing subscription plans...")
        init_subscription_plans_standalone()
        print("✅ Subscription plans initialization complete!")
    else:
        # Run full migration
        main()