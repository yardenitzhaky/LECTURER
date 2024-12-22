# app/db/models/lecture.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    status = Column(String(50))  # e.g., "completed", "processing", "failed"
    
    # Relationships
    transcription_segments = relationship("TranscriptionSegment", back_populates="lecture")