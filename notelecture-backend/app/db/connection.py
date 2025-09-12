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
# Convert PostgreSQL URL for async usage
if settings.DATABASE_URL.startswith("postgresql://"):
    async_database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif settings.DATABASE_URL.startswith("mysql+pymysql://"):
    # Fallback for MySQL (legacy support)
    async_database_url = settings.DATABASE_URL.replace("mysql+pymysql://", "mysql+aiomysql://")
else:
    async_database_url = settings.DATABASE_URL

# Configure asyncpg for serverless environments like Vercel
connect_args = {
    "server_settings": {
        "application_name": "notelecture_vercel",
        "jit": "off"  # Disable JIT for better compatibility
    },
    "command_timeout": 30,
    "ssl": "require" if "sslmode" not in async_database_url else None
}

# Add connection pooling configuration optimized for serverless
async_engine = create_async_engine(
    async_database_url,
    connect_args=connect_args,
    pool_size=1,  # Minimal pool for serverless
    max_overflow=0,  # No overflow in serverless
    pool_pre_ping=True,  # Validate connections
    pool_recycle=300,  # Recycle connections every 5 minutes
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