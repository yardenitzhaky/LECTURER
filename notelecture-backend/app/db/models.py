# app/db/models.py
from typing import Any
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
import uuid
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from datetime import datetime, timedelta


class Base(DeclarativeBase):
    id: Any

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    
    # Additional user fields beyond FastAPI-Users defaults
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    free_lectures_used = Column(Integer, default=0)
    
    # Relationships
    lectures = relationship("Lecture", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    
    def can_create_lecture_sync(self, current_sub=None):
        """Check if user can create a new lecture (for sync contexts)"""
        if current_sub:
            return current_sub.lectures_used < current_sub.plan.lecture_limit
        else:
            # Free user - 3 lectures limit
            return self.free_lectures_used < 3

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    status = Column(String(50), index=True)
    video_path = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    notes = Column(Text, nullable=True)

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
    image_data = Column(Text) # PostgreSQL TEXT can handle large data


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

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # "Weekly", "Monthly", "6 Months", "12 Months"
    duration_days = Column(Integer, nullable=False)  # 7, 30, 180, 365
    price = Column(Numeric(10, 2), nullable=False)  # Price in dollars
    lecture_limit = Column(Integer, nullable=False)  # Max lectures per subscription period
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="plan")

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    lectures_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    
    def is_expired(self):
        """Check if subscription is expired"""
        return datetime.utcnow() > self.end_date
    
    def days_remaining(self):
        """Get days remaining in subscription"""
        if self.is_expired():
            return 0
        return (self.end_date - datetime.utcnow()).days

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True)
    paypal_order_id = Column(String(255), nullable=False, unique=True, index=True)
    paypal_payment_id = Column(String(255), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(50), default="pending", index=True)  # pending, completed, failed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    subscription = relationship("UserSubscription")