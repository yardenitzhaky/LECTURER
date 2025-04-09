# app/main.py
import logging
import logging.config # Keep this if you plan advanced config later
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Keep if needed

from app.api import api
from app.core.config import settings


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

# --- Set up CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"], # Consider restricting methods (e.g., ["GET", "POST"])
    allow_headers=["*"], # Consider restricting headers
)

# --- Include Routers ---
app.include_router(api.router, prefix="/api")
logger.info("API router included at prefix /api")
