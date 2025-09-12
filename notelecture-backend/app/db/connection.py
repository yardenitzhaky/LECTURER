# app/db/connection.py
"""
Database connection setup for both sync and async operations.
"""
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Sync database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async database setup
# Convert PostgreSQL URL for async usage and handle connection pooling
if settings.DATABASE_URL.startswith("postgresql://"):
    async_database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    # For Supabase/serverless environments, prefer pooled connections
    # Convert direct connection (:5432) to pooled connection (:6543)
    if "supabase.co:5432" in async_database_url:
        async_database_url = async_database_url.replace(":5432", ":6543")
        print(f"Using Supabase connection pooler: {async_database_url.split('@')[1]}")
    elif ".supabase.co/" in async_database_url and ":6543" not in async_database_url:
        # If it's a Supabase URL without explicit port, add pooler port
        async_database_url = async_database_url.replace(".supabase.co/", ".supabase.co:6543/")
        print(f"Using Supabase connection pooler: {async_database_url.split('@')[1]}")
        
elif settings.DATABASE_URL.startswith("mysql+pymysql://"):
    # Fallback for MySQL (legacy support)
    async_database_url = settings.DATABASE_URL.replace("mysql+pymysql://", "mysql+aiomysql://")
else:
    async_database_url = settings.DATABASE_URL

# Configure asyncpg for serverless environments like Vercel
import os
connect_args = {
    "server_settings": {
        "application_name": "notelecture_vercel",
        "jit": "off",  # Disable JIT for better compatibility
        "tcp_keepalives_idle": "300",
        "tcp_keepalives_interval": "30", 
        "tcp_keepalives_count": "3"
    },
    "command_timeout": 60  # Increased timeout for serverless cold starts
}

# Add SSL configuration for production
if "supabase.co" in async_database_url or os.getenv("VERCEL"):
    connect_args["ssl"] = "require"

# Add connection pooling configuration optimized for serverless
async_engine = create_async_engine(
    async_database_url,
    connect_args=connect_args,
    pool_size=0,  # No persistent pool in serverless
    max_overflow=0,  # No overflow in serverless  
    poolclass=None,  # Disable connection pooling entirely
    pool_pre_ping=False,  # Skip pre-ping since no pool
    echo=False
)

AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def get_session():
    """Get sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        yield session