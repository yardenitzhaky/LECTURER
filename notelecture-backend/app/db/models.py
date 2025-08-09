# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import MEDIUMTEXT, LONGTEXT
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from datetime import datetime
import uuid

from app.db.base_class import Base

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    
    # Additional user fields beyond FastAPI-Users defaults
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to lectures
    lectures = relationship("Lecture", back_populates="user", cascade="all, delete-orphan")

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    status = Column(String(50), index=True)
    video_path = Column(Text)
    presentation_path = Column(String(255)) # This field is not used, consider removing or implementing it
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

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
    user = relationship("User", back_populates="lectures")

class Slide(Base):
    __tablename__ = "slides"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    index = Column(Integer, nullable=False)
    image_data = Column(MEDIUMTEXT) # Use the imported type directly
    # If you need even more space, use LONGTEXT:
    # image_data = Column(LONGTEXT)


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