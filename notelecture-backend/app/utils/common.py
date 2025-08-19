"""Common utility functions for authentication, database, and general purpose."""

import uuid
import secrets
from typing import Generator
from passlib.context import CryptContext
from app.db.connection import SessionLocal

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Database Dependencies ---
def get_db() -> Generator:
    """Database dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Authentication Utilities ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def generate_secret_key(length: int = 32) -> str:
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(length)


def is_valid_uuid(uuid_string: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False