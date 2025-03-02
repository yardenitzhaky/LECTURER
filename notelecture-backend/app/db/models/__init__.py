# app/db/models/__init__.py
from app.db.models.Lecture import Lecture
from app.db.models.Slide import Slide
from app.db.models.TranscriptionSegment import TranscriptionSegment

__all__ = ['Lecture', 'Slide', 'TranscriptionSegment']