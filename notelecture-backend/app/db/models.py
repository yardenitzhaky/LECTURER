# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text 
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Lecture(Base):
    __tablename__ = "lectures" 

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    status = Column(String(50), index=True)
    video_path = Column(Text) 
    presentation_path = Column(String(255)) 

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
    __tablename__ = "slides" 

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    index = Column(Integer, nullable=False)
    image_data = Column(Text)
    summary = Column(Text, nullable=True)

    lecture = relationship("Lecture", back_populates="slides")

class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments" 

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    start_time = Column(Float, index=True)
    end_time = Column(Float)
    text = Column(Text) 
    confidence = Column(Float)
    slide_index = Column(Integer, nullable=False, default=0, index=True)

    lecture = relationship("Lecture", back_populates="transcription_segments")