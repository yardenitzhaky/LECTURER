# app/main.py
import logging
import logging.config # Keep this if you plan advanced config later
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Keep if needed

from app.api import api
from app.api import oauth
from app.core.config import settings
from app.auth import fastapi_users, auth_backend, google_oauth_client
from app.schemas import UserRead, UserCreate, UserUpdate


# --- Basic Logging Configuration ---
# Configure this BEFORE creating the FastAPI app instance.
# This sets up the root logger. Logs from your app and Uvicorn will use this config.
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level you want to see (e.g., INFO, DEBUG)
    format="%(asctime)s - %(levelname)-8s - [%(name)s] - %(message)s", # Include logger name
    datefmt="%Y-%m-%d %H:%M:%S",
    # handlers=[logging.StreamHandler()] # Default is StreamHandler (console), explicit is fine too
)

# Get a logger for this main module (optional, but good practice)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(title=settings.PROJECT_NAME)
logger.info(f"Configured logging. Starting {settings.PROJECT_NAME} application...") # Test log

# --- Add middleware to handle database errors ---
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError

@app.middleware("http")
async def handle_db_errors(request: Request, call_next):
    """Handle database connection errors gracefully."""
    try:
        response = await call_next(request)
        return response
    except (InterfaceError, OperationalError) as e:
        logger.error(f"Database connection error: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"detail": "Database connection error. Please try again."},
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
                "Access-Control-Allow-Credentials": "true",
            }
        )

# --- Set up CORS ---
# Use origins from environment variable, with fallback to hardcoded list
allowed_origins = settings.BACKEND_CORS_ORIGINS if settings.BACKEND_CORS_ORIGINS else [
    "http://localhost:5173",  # Local development
    "http://localhost:3000",  # Alternative local dev
    "https://lecturer.it.com", # Production frontend
    "https://notelecture-frontend.vercel.app", # Vercel frontend
    "https://notelecture-frontend-yardens-projects-1b88cd04.vercel.app", # Vercel preview
]

# Log the configured origins for debugging
logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to the client
)

# --- Include Authentication Routers ---
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/api/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), prefix="/api/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/api/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/api/auth",
    tags=["auth"],
)
# Commented out to use custom HTTP-based users router instead
# app.include_router(
#     fastapi_users.get_users_router(UserRead, UserUpdate),
#     prefix="/api/users",
#     tags=["users"],
# )
app.include_router(
    oauth.router,
    prefix="/api/auth/google",
    tags=["auth"],
)

# --- Include API Routers ---
app.include_router(api.router, prefix="/api")
logger.info("API router included at prefix /api")
