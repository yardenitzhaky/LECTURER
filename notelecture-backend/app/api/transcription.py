# app/api/transcription.py
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import aiofiles
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.utils.common import get_db
from app.core.config import settings
from app.db.models import Lecture, Slide, User, UserSubscription
from app.auth import current_active_user
from app.db.session import SessionLocal
from app.services.presentation import PresentationService
from app.utils.database import update_lecture_status
from app.api.background_tasks import process_video_background

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
presentation_service = PresentationService()


@router.post("/transcribe/", status_code=202)
async def transcribe_lecture(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user),
    presentation: UploadFile = File(...),
    video: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """
    Accepts presentation and video (file or URL), starts background processing.
    """
    if not video and not video_url:
        raise HTTPException(status_code=400, detail="Either video file or video URL must be provided.")
    if video and video_url:
        raise HTTPException(status_code=400, detail="Provide either video file or video URL, not both.")

    upload_dir = Path(settings.UPLOADS_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    lecture_id = None

    try:
        # Check subscription limits before processing
        from datetime import datetime
        now = datetime.utcnow()
        current_sub = db.query(UserSubscription).filter(
            UserSubscription.user_id == str(current_user.id),
            UserSubscription.is_active == True,
            UserSubscription.start_date <= now,
            UserSubscription.end_date >= now
        ).first()
        
        if not current_user.can_create_lecture_sync(current_sub):
            if current_sub:
                raise HTTPException(
                    status_code=403, 
                    detail=f"You have reached your lecture limit ({current_sub.plan.lecture_limit}) for your {current_sub.plan.name} plan. Please upgrade or wait for your next billing period."
                )
            else:
                raise HTTPException(
                    status_code=403,
                    detail=f"You have reached your free lecture limit (3). Please subscribe to a plan to continue creating lectures."
                )
        
        # Handle presentation file
        presentation_filename = presentation.filename or "presentation"
        presentation_content = await presentation.read()
        file_extension = Path(presentation_filename).suffix.lower().lstrip('.')
        if file_extension not in ['pptx', 'pdf', 'ppt']:
            raise HTTPException(status_code=400, detail="Unsupported presentation file type. Use PPTX or PDF.")

        # Handle video input
        video_path_str: str
        original_video_filename = "video_from_url"
        if video:
            original_video_filename = video.filename or "uploaded_video"
            video_filename = f"{uuid.uuid4()}{Path(original_video_filename).suffix}"
            video_path_obj = upload_dir / video_filename
            async with aiofiles.open(video_path_obj, 'wb') as out_file:
                await out_file.write(await video.read())
            video_path_str = str(video_path_obj)
            logger.info(f"Saved uploaded video to: {video_path_str}")
        else:
            video_path_str = video_url
            logger.info(f"Using video URL: {video_path_str[:100]}...")

        # Create initial lecture record
        lecture_title = Path(presentation_filename).stem or Path(original_video_filename).stem or "Untitled Lecture"
        lecture = Lecture(title=lecture_title, status="pending", video_path=video_path_str, user_id=str(current_user.id))
        db.add(lecture)
        db.flush()
        lecture_id = lecture.id
        logger.info(f"Created Lecture record ID: {lecture_id}, Status: pending")

        # Process and save slides
        update_lecture_status(db, lecture_id, "processing_slides")
        try:
            slide_images = await presentation_service.process_presentation(presentation_content, file_extension)
            slides_to_add = [Slide(lecture_id=lecture_id, index=i, image_data=img) for i, img in enumerate(slide_images)]
            if slides_to_add:
                db.add_all(slides_to_add)
            db.commit()
            logger.info(f"Saved {len(slides_to_add)} slides for lecture ID: {lecture_id}")
        except Exception as pres_err:
            update_lecture_status(db, lecture_id, "failed")
            raise HTTPException(status_code=500, detail=f"Error processing presentation: {pres_err}") from pres_err

        # Update usage count
        if current_sub:
            current_sub.lectures_used += 1
        else:
            current_user.free_lectures_used += 1
        db.commit()

        # Enqueue background task
        background_tasks.add_task(process_video_background, video_path_or_url=video_path_str, lecture_id=lecture_id, db_session_factory=SessionLocal)
        update_lecture_status(db, lecture_id, "processing")

        return {"message": "Processing started", "lecture_id": lecture_id}

    except Exception as e:
        logger.error(f"Error in /transcribe/ (Lecture ID: {lecture_id or 'N/A'}): {e}", exc_info=True)
        if lecture_id and not isinstance(e, HTTPException):
            try:
                update_lecture_status(db, lecture_id, "failed")
            except Exception as status_err:
                logger.error(f"Failed to mark lecture {lecture_id} as failed during error handling: {status_err}")
        elif not lecture_id:
            db.rollback()

        # Re-raise HTTPExceptions, wrap others
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=f"Server error during upload: {str(e)}")