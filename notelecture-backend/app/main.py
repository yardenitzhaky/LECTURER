# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import transcription
from app.core.config import settings
from fastapi.staticfiles import StaticFiles
import os


app = FastAPI(title=settings.PROJECT_NAME)

# Create directories if they don't exist
os.makedirs("uploads/slides", exist_ok=True)

# Mount the uploads directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcription.router, prefix="/api")