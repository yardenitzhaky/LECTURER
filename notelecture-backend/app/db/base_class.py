# app/db/base_class.py
from typing import Any
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    id: Any 
    pass 