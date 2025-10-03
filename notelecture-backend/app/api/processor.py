# app/api/processor.py
"""
Manual lecture processor endpoint.
This endpoint processes pending lectures synchronously.
Can be called manually or via Vercel Cron Jobs.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.utils.common import get_db
from app.db.models import Lecture
from app.api.background_tasks import process_video_background
from app.db.connection import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/process-pending", status_code=200)
async def process_pending_lectures(
    db: Session = Depends(get_db),
    limit: int = 1
) -> Dict[str, Any]:
    """
    Process pending lectures that are stuck in 'processing' status.
    This is a workaround for Vercel serverless not supporting background tasks.

    Query Parameters:
    - limit: Number of lectures to process (default: 1)
    """
    try:
        # Find lectures stuck in processing status
        pending_lectures = db.query(Lecture).filter(
            Lecture.status == "processing"
        ).limit(limit).all()

        if not pending_lectures:
            return {
                "message": "No pending lectures to process",
                "processed": 0
            }

        processed_count = 0
        errors = []

        for lecture in pending_lectures:
            try:
                logger.info(f"Processing lecture {lecture.id}: {lecture.title}")

                # Process the lecture synchronously
                await process_video_background(
                    video_path_or_url=lecture.video_path,
                    lecture_id=lecture.id,
                    db_session_factory=SessionLocal
                )

                processed_count += 1
                logger.info(f"Successfully processed lecture {lecture.id}")

            except Exception as e:
                error_msg = f"Failed to process lecture {lecture.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        return {
            "message": f"Processed {processed_count} lecture(s)",
            "processed": processed_count,
            "total_pending": len(pending_lectures),
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.error(f"Error in process_pending_lectures: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", status_code=200)
async def get_processor_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get the status of all lectures and pending processing queue.
    """
    try:
        # Count lectures by status
        from sqlalchemy import func

        status_counts = db.query(
            Lecture.status,
            func.count(Lecture.id).label('count')
        ).group_by(Lecture.status).all()

        status_dict = {status: count for status, count in status_counts}

        # Get pending lectures details
        pending_lectures = db.query(Lecture).filter(
            Lecture.status == "processing"
        ).all()

        pending_details = [
            {
                "id": lecture.id,
                "title": lecture.title,
                "created_at": lecture.created_at.isoformat() if lecture.created_at else None,
                "video_path": lecture.video_path[:100] + "..." if len(lecture.video_path or "") > 100 else lecture.video_path
            }
            for lecture in pending_lectures
        ]

        return {
            "status_counts": status_dict,
            "pending_count": status_dict.get("processing", 0),
            "pending_lectures": pending_details
        }

    except Exception as e:
        logger.error(f"Error in get_processor_status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
