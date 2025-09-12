# app/api/api.py
import logging
from fastapi import APIRouter

from app.api import transcription, lectures, summarization, subscriptions, health, users

logger = logging.getLogger(__name__)

# Create main API router
router = APIRouter()

# Include all sub-routers
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(transcription.router, tags=["transcription"])
router.include_router(lectures.router, tags=["lectures"])
router.include_router(summarization.router, tags=["summarization"])
router.include_router(subscriptions.router, tags=["subscriptions"])