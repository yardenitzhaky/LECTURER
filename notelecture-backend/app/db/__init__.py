# app/db/__init__.py
from .base_class import Base
from .session import SessionLocal, engine
from .models import Lecture, Slide, TranscriptionSegment

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "Lecture",
    "Slide",
    "TranscriptionSegment",
]