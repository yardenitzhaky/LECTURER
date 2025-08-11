# app/api/api.py
import logging
from fastapi import APIRouter

from app.api import transcription, lectures, summarization

logger = logging.getLogger(__name__)

# Create main API router
router = APIRouter()

# Include all sub-routers
router.include_router(transcription.router, tags=["transcription"])
router.include_router(lectures.router, tags=["lectures"])
router.include_router(summarization.router, tags=["summarization"])