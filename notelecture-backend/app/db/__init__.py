# app/db/__init__.py (קובץ מעודכן)
from .base_class import Base
from .session import SessionLocal, engine # Expose engine if needed elsewhere, e.g., for Alembic
from .models import Lecture, Slide, TranscriptionSegment

# Optional: Define __all__ for cleaner imports if using `from app.db import *` (though explicit imports are preferred)
__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "Lecture",
    "Slide",
    "TranscriptionSegment",
]