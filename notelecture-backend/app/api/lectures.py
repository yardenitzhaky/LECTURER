# app/api/lectures.py
import os
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.utils.common import get_db, get_async_db
from app.db.models import Lecture, Slide, TranscriptionSegment, User
from app.auth import current_active_user
from app.schemas import UpdateLectureRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/lectures/")
async def get_user_lectures(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get all lectures for the current user."""
    try:
        result = await db.execute(
            select(Lecture).filter(Lecture.user_id == str(current_user.id)).order_by(Lecture.id.desc())
        )
        lectures = result.scalars().all()
        
        return {
            "lectures": [{
                "id": lecture.id,
                "title": lecture.title,
                "status": lecture.status,
                "video_path": lecture.video_path,
                "notes": lecture.notes
            } for lecture in lectures]
        }
    except Exception as e:
        logger.error(f"Error retrieving lectures for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving lectures: {str(e)}")


@router.get("/lectures/{lecture_id}/transcription")
async def get_lecture_transcription(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Retrieve lecture data including metadata, slides, and transcription."""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.user_id == str(current_user.id)).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    logger.info(f"Fetching lecture {lecture_id} (Status: {lecture.status})")

    try:
        slides = db.query(Slide).filter(Slide.lecture_id == lecture_id).order_by(Slide.index).all()
        segments = db.query(TranscriptionSegment).filter(TranscriptionSegment.lecture_id == lecture_id).order_by(TranscriptionSegment.start_time).all()

        return {
            "lecture_id": lecture.id,
            "title": lecture.title,
            "status": lecture.status,
            "notes": lecture.notes,
            "slides": [{"imageUrl": s.image_data, "index": s.index, "summary": s.summary} for s in slides],
            "transcription": [{
                "id": seg.id, "startTime": seg.start_time, "endTime": seg.end_time,
                "text": seg.text, "confidence": seg.confidence, "slideIndex": seg.slide_index
             } for seg in segments]
        }
    except Exception as e:
        logger.error(f"Error retrieving data for lecture {lecture_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving lecture data: {str(e)}")


@router.put("/lectures/{lecture_id}")
async def update_lecture(
    lecture_id: int,
    request: UpdateLectureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Update lecture title and/or notes."""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.user_id == str(current_user.id)).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    try:
        if request.title is not None:
            lecture.title = request.title
        if request.notes is not None:
            lecture.notes = request.notes
            
        db.commit()
        logger.info(f"Updated lecture {lecture_id} for user {current_user.id}")
        
        return {
            "id": lecture.id,
            "title": lecture.title,
            "status": lecture.status,
            "video_path": lecture.video_path,
            "notes": lecture.notes
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating lecture {lecture_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating lecture: {str(e)}")


@router.delete("/lectures/{lecture_id}")
async def delete_lecture(
    lecture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, str]:
    """Delete a lecture and all its associated data."""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.user_id == str(current_user.id)).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    try:
        # Delete video file if it exists locally
        if lecture.video_path and not lecture.video_path.startswith(('http://', 'https://')):
            if os.path.exists(lecture.video_path):
                try:
                    os.remove(lecture.video_path)
                    logger.info(f"Deleted video file: {lecture.video_path}")
                except Exception as file_err:
                    logger.warning(f"Could not delete video file {lecture.video_path}: {file_err}")
        
        # Database cascades will handle slides and transcription_segments deletion
        db.delete(lecture)
        db.commit()
        
        logger.info(f"Deleted lecture {lecture_id} for user {current_user.id}")
        return {"message": "Lecture deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting lecture {lecture_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting lecture: {str(e)}")