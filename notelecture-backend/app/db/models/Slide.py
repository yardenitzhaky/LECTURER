# app/db/models/Slide.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Slide(Base):
    __tablename__ = "slides"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    index = Column(Integer)
    image_data = Column(String(255))
    
    # Relationships
    lecture = relationship("Lecture", back_populates="slides")
    
    def to_dict(self):
        return {
            "id": self.id,
            "lecture_id": self.lecture_id,
            "index": self.index,
            "image_data": self.image_data
        }