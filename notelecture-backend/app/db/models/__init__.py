# app/db/models/__init__.py
from app.db.models.transcription import TranscriptionSegment
from app.db.models.lecture import Lecture  # We'll create this next

__all__ = ["TranscriptionSegment", "Lecture"]