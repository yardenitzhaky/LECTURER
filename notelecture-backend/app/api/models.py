# app/api/models.py
from typing import Optional
from pydantic import BaseModel

class SummarizeRequest(BaseModel):
    custom_prompt: Optional[str] = None

class UpdateLectureRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None