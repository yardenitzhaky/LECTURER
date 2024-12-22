# app/db/models/transcription.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

# app/db/models/transcription.py
class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    start_time = Column(Float)
    end_time = Column(Float)
    text = Column(String(1000))
    confidence = Column(Float)
    slide_id = Column(Integer, ForeignKey("slides.id"), nullable=True)

    # Relationship
    lecture = relationship("Lecture", back_populates="transcription_segments")
    slide = relationship("Slide", back_populates="segments")