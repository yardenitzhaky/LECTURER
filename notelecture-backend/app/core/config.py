# app/core/config.py

import json
from typing import List
from pydantic_settings import BaseSettings
from typing import Any, Dict, Optional
from pydantic import field_validator

class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables or .env file.
    BaseSettings automatically reads environment variables into these fields.
    """
    # Core application settings
    PROJECT_NAME: str
    BACKEND_CORS_ORIGINS: Optional[List[str]] = None
    DATABASE_URL: str
    UPLOADS_DIR: str
    
    # Authentication related settings
    SECRET_KEY: str  # Secret key used for token signing
    ALGORITHM: str  # Algorithm used for JWT token encoding (usually HS256)
    ACCESS_TOKEN_EXPIRE_MINUTES: int  # Token expiration time in minutes
    openai_api_key: Optional[str] = None  # OpenAI API key for external service
    runpod_api_key: Optional[str] = None  # RunPod API key for transcription service
    runpod_endpoint_id: Optional[str] = None  # RunPod endpoint ID for transcription service
    
    # Google OAuth settings
    GOOGLE_OAUTH_CLIENT_ID: str
    GOOGLE_OAUTH_CLIENT_SECRET: str
    FRONTEND_URL: str = "http://localhost:5173"
    
    # Supabase settings (optional)
    supabase_access_token: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # PayPal settings
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"  # sandbox or live
    
    # Vercel settings
    VERCEL_TOKEN: Optional[str] = None
    
    # External service configuration
    EXTERNAL_SERVICE_URL: str = ""
    EXTERNAL_SERVICE_API_KEY: str = ""

    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If it's a single origin string, return as list
                return [v]
        return v

    class Config:
        """
        Configuration for the Settings class.
        Specifies how settings should be loaded and processed.
        """
        env_file = ".env"  # Path to the environment file
        env_file_encoding = 'utf-8'  # Encoding of the environment file

# Create a global settings instance for use throughout the application
settings = Settings()