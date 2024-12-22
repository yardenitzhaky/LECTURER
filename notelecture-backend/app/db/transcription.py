# app/db/models/transcription.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    start_time = Column(Float)  # Time in seconds
    end_time = Column(Float)
    text = Column(String(1000))
    speaker = Column(String(100), nullable=True)  # Optional speaker identification
    confidence = Column(Float)

    # Relationship
    lecture = relationship("Lecture", back_populates="transcription_segments")

class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("transcription_segments.id"))
    text = Column(String(100))
    start_time = Column(Float)
    end_time = Column(Float)
    confidence = Column(Float)
    
    # Relationship
    segment = relationship("TranscriptionSegment", back_populates="words")