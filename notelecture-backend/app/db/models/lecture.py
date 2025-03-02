# app/db/models/lecture.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    status = Column(String(50))
    video_path = Column(String(255))
    presentation_path = Column(String(255))
    
    # Relationships
    transcription_segments = relationship("TranscriptionSegment", back_populates="lecture")
    slides = relationship("Slide", back_populates="lecture") 

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "video_path": self.video_path,
            "presentation_path": self.presentation_path
        }