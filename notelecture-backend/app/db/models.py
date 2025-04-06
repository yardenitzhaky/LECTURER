# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text # Import Text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Lecture(Base):
    __tablename__ = "lectures" # Explicitly define table name

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    status = Column(String(50), index=True)
    video_path = Column(Text) # Changed to Text for potentially long URLs/paths
    presentation_path = Column(String(255)) # Still here, remove if unused

    # Relationships
    transcription_segments = relationship(
        "TranscriptionSegment",
        back_populates="lecture",
        cascade="all, delete-orphan"
    )
    slides = relationship(
        "Slide",
        back_populates="lecture",
        cascade="all, delete-orphan"
    )

class Slide(Base):
    __tablename__ = "slides" # Explicitly define table name

    id = Column(Integer, primary_key=True, index=True)
    # Ensure ForeignKey points to the EXPLICIT table name 'lectures.id'
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    index = Column(Integer, nullable=False)
    # IMPORTANT: Use Text for base64 data, not String(255)
    image_data = Column(Text)

    # Relationships
    lecture = relationship("Lecture", back_populates="slides")

class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments" # Explicitly define table name

    id = Column(Integer, primary_key=True, index=True)
    # Ensure ForeignKey points to the EXPLICIT table name 'lectures.id'
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    start_time = Column(Float, index=True)
    end_time = Column(Float)
    text = Column(Text) # Changed to Text for potentially long segments
    confidence = Column(Float)
    slide_index = Column(Integer, nullable=False, default=0, index=True)

    # Relationship
    lecture = relationship("Lecture", back_populates="transcription_segments")