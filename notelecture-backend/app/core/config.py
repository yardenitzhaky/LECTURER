# app/core/config.py

from typing import List
from pydantic_settings import BaseSettings
from typing import Any, Dict, Optional

class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables or .env file.
    BaseSettings automatically reads environment variables into these fields.
    """
    # Core application settings
    PROJECT_NAME: str  
    BACKEND_CORS_ORIGINS: List[str]  
    DATABASE_URL: str
    UPLOADS_DIR: str
    
    # Authentication related settings
    SECRET_KEY: str  # Secret key used for token signing
    ALGORITHM: str  # Algorithm used for JWT token encoding (usually HS256)
    ACCESS_TOKEN_EXPIRE_MINUTES: int  # Token expiration time in minutes
    openai_api_key: Optional[str] = None  # OpenAI API key for external service
    
    # AWS credentials for S3 or other AWS services
    aws_access_key_id: Optional[str] = None  # AWS access key for API authentication
    aws_secret_access_key: Optional[str] = None  # AWS secret key for API authentication
    aws_default_region: Optional[str] = None  # Default AWS region for services
    ivrit_ai_api_key: Optional[str] = None  # API key for IVRIT.AI transcription service

    class Config:
        """
        Configuration for the Settings class.
        Specifies how settings should be loaded and processed.
        """
        env_file = ".env"  # Path to the environment file
        env_file_encoding = 'utf-8'  # Encoding of the environment file

# Create a global settings instance for use throughout the application
settings = Settings()