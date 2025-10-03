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
engine = create_engine(
    settings.DATABASE_URL,
    # Disable prepared statements for pgbouncer compatibility
    execution_options={"compiled_cache": None}
)
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
from uuid import uuid4

# Generate unique prepared statement names for pgbouncer compatibility
def generate_unique_prepared_statement_name():
    """Generate unique prepared statement names to avoid conflicts with pgbouncer."""
    return f"__asyncpg_{uuid4().hex[:8]}__"

connect_args = {
    "server_settings": {
        "application_name": "notelecture_vercel",
        "jit": "off",  # Disable JIT for better compatibility
    },
    "command_timeout": 30,  # Allow enough time for connection cleanup
    "timeout": 30,  # Connection timeout
    "statement_cache_size": 0,  # CRITICAL: Disable prepared statements completely
    "prepared_statement_cache_size": 0,  # Disable prepared statement cache
    "prepared_statement_name_func": generate_unique_prepared_statement_name,  # Use UUID-based names
}

# Add SSL configuration for production
if "supabase.co" in async_database_url or os.getenv("VERCEL"):
    connect_args["ssl"] = "require"

# Add connection pooling configuration optimized for serverless
from sqlalchemy.pool import NullPool

# CRITICAL: Add pgbouncer compatibility parameters to the URL
# This disables prepared statements at the connection level
if "?" in async_database_url:
    async_database_url += "&prepared_statement_cache_size=0&statement_cache_size=0"
else:
    async_database_url += "?prepared_statement_cache_size=0&statement_cache_size=0"

async_engine = create_async_engine(
    async_database_url,
    connect_args=connect_args,
    poolclass=NullPool,  # Use NullPool for serverless environments
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_pre_ping=False,  # CRITICAL: Disable pre-ping to avoid prepared statements
    echo=False,
    # NUCLEAR OPTION: Force all statements to execute as plain text
    execution_options={
        "compiled_cache": None,  # Disable compiled cache
        "render_postcompile": True,  # Force inline parameter rendering
        "autocommit": False,  # Use explicit transaction control
    },
    future=True
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Prevent automatic flushes
    autocommit=False  # Ensure explicit commits
)


def get_session():
    """Get sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with proper isolation for serverless and pgbouncer compatibility."""
    session = None
    try:
        # Create a fresh sessionmaker for each request to avoid event loop binding issues
        # This prevents the "bound to different event loop" error in serverless environments
        fresh_sessionmaker = sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        session = fresh_sessionmaker()

        # For debugging: log connection info
        print(f"Created new async session for request")

        yield session
    except Exception as e:
        print(f"Session error occurred: {type(e).__name__}: {e}")
        if session:
            try:
                await session.rollback()  # Rollback on error
            except Exception as rollback_error:
                print(f"Error during rollback: {rollback_error}")
        raise e
    finally:
        if session:
            try:
                # Close session with timeout protection
                import asyncio
                await asyncio.wait_for(session.close(), timeout=10.0)
                print(f"Successfully closed async session")
            except asyncio.TimeoutError:
                print(f"Session close timed out - ignoring (connection will be cleaned up by pool)")
            except Exception as close_error:
                print(f"Error closing session: {close_error}")  # Log but don't raise