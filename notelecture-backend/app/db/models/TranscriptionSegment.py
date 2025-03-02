# app/db/models/transcription.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    start_time = Column(Float)
    end_time = Column(Float)
    text = Column(String(1000))
    confidence = Column(Float)
    slide_index = Column(Integer, nullable=False, default=0)

    # Relationship
    lecture = relationship("Lecture", back_populates="transcription_segments")

    def to_dict(self):
        return {
            "id": self.id,
            "lectureId": self.lecture_id,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "text": self.text,
            "confidence": self.confidence,
            "slideIndex": self.slide_index,
        }
