# app/schemas.py
import uuid
from typing import Optional
from datetime import datetime
from fastapi_users import schemas
from pydantic import BaseModel


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: Optional[datetime] = None


class UserCreate(schemas.BaseUserCreate):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# API Request Models
class SummarizeRequest(BaseModel):
    custom_prompt: Optional[str] = None


class UpdateLectureRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None