# app/db/models/__init__.py
from app.db.models.lecture import Lecture
from app.db.models.transcription import TranscriptionSegment
from app.db.models.Slide import Slide

__all__ = ["TranscriptionSegment", "Lecture", "Slide"]