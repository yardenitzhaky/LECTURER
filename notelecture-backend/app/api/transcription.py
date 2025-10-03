# app/api/transcription.py
import uuid
import logging
import tempfile
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

import aiofiles
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.utils.common import get_db
from app.core.config import settings
from app.db.models import Lecture, Slide, User, UserSubscription
from app.auth import current_active_user
from app.db.connection import SessionLocal
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

    # Use /tmp directory for Vercel serverless environment
    upload_dir = Path("/tmp")
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
        
        # Log current usage before processing
        logger.info(f"Before processing - User {current_user.id} free_lectures_used: {current_user.free_lectures_used}")
        if current_sub:
            logger.info(f"Before processing - Subscription {current_sub.id} lectures_used: {current_sub.lectures_used}")
        
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
        
        # Increment usage count immediately after verifying limits
        if current_sub:
            logger.info(f"Updating subscription usage: {current_sub.lectures_used} -> {current_sub.lectures_used + 1}")
            current_sub.lectures_used += 1
        else:
            # Refresh user from database to ensure we have the current session object
            db_user = db.query(User).filter(User.id == current_user.id).first()
            if db_user:
                logger.info(f"Updating free lectures usage for user {current_user.id}: {db_user.free_lectures_used} -> {db_user.free_lectures_used + 1}")
                db_user.free_lectures_used += 1
            else:
                logger.error(f"Could not find user {current_user.id} in database for usage update")
                raise HTTPException(status_code=500, detail="Database error: Could not update user usage counter")
        
        # Commit the usage increment before processing to ensure it's persistent
        db.commit()
        logger.info("Usage count increment committed successfully")
        
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
            # Use tempfile for better temp file handling
            suffix = Path(original_video_filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='/tmp') as tmp_file:
                video_content = await video.read()
                logger.info(f"Read {len(video_content)} bytes from uploaded video")
                bytes_written = tmp_file.write(video_content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                video_path_str = tmp_file.name
            logger.info(f"Saved uploaded video to temp file: {video_path_str} ({bytes_written} bytes written)")
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

        # Instead of background task, call external Cloud Run service
        update_lecture_status(db, lecture_id, "processing")
        db.commit()

        # Trigger processing on external Cloud Run service
        try:
            import httpx

            # Prepare slides data for external service
            slides_list = [
                {"index": slide.index, "image_data": slide.image_data}
                for slide in db.query(Slide).filter(Slide.lecture_id == lecture_id).order_by(Slide.index).all()
            ]

            # Get backend URL from settings
            backend_url = settings.BACKEND_URL or "https://notelecture-backend.vercel.app"

            # Call external service
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare data for multipart form
                data = {
                    "lecture_id": str(lecture_id),
                    "slides_data": json.dumps(slides_list),
                    "backend_url": backend_url,
                    "api_key": settings.EXTERNAL_SERVICE_API_KEY or ""
                }

                # If video file was uploaded, send it to Cloud Run
                # If video URL, just send the URL
                if video:
                    # Re-read the video file and send to Cloud Run
                    logger.info(f"Reading video file from: {video_path_str}")
                    if not os.path.exists(video_path_str):
                        logger.error(f"Video file does not exist: {video_path_str}")
                        raise HTTPException(status_code=500, detail="Video file not found")

                    video_file_size = os.path.getsize(video_path_str)
                    logger.info(f"Video file size on disk: {video_file_size} bytes")

                    # Read entire file into memory to ensure complete upload
                    with open(video_path_str, 'rb') as video_file:
                        video_bytes = video_file.read()
                        logger.info(f"Read {len(video_bytes)} bytes from video file")

                        files = {
                            "video_file": (original_video_filename, video_bytes, "video/mp4")
                        }
                        response = await client.post(
                            f"{settings.EXTERNAL_SERVICE_URL}/process-lecture-complete/",
                            data=data,
                            files=files
                        )
                else:
                    # For URL, just send as form data
                    data["video_url"] = video_url
                    response = await client.post(
                        f"{settings.EXTERNAL_SERVICE_URL}/process-lecture-complete/",
                        data=data
                    )

                response.raise_for_status()
                logger.info(f"Triggered external processing for lecture {lecture_id}: {response.status_code}")

        except Exception as ext_err:
            logger.error(f"Failed to trigger external processing: {ext_err}", exc_info=True)
            # Mark as failed so user knows
            update_lecture_status(db, lecture_id, "failed")
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(ext_err)}")
        finally:
            # Clean up temp video file if it was created
            if video and video_path_str and os.path.exists(video_path_str):
                try:
                    os.unlink(video_path_str)
                    logger.info(f"Cleaned up temp video file: {video_path_str}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp video file {video_path_str}: {cleanup_err}")

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