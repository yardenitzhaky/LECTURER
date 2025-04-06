# app/api/api.py
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os
from pathlib import Path
import aiofiles
import uuid
import base64
import io # Keep io for potential future use, though not directly used now

from app.services.transcription import TranscriptionService
from app.services.presentation import PresentationService
from app.services.slide_matching import SlideMatchingService
from app.db.models import Lecture, TranscriptionSegment, Slide
from app import deps
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
transcription_service = TranscriptionService()
presentation_service = PresentationService()
slide_matching_service = SlideMatchingService()

# --- Helper Function ---
def _update_lecture_status(db: Session, lecture_id: int, status: str):
    """Helper function to update lecture status in the database."""
    try:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if lecture:
            lecture.status = status
            db.commit()
            logger.info(f"Lecture ID {lecture_id} status updated to: {status}")
        else:
            logger.warning(f"Attempted to update status for non-existent lecture ID: {lecture_id}")
    except Exception as e:
        db.rollback() # Rollback on error during status update
        logger.error(f"Failed to update status for lecture {lecture_id} to {status}: {e}")
        raise # Re-raise the exception to be handled by the caller


# --- API Endpoints ---

@router.post("/transcribe/")
async def transcribe_lecture(
    background_tasks: BackgroundTasks,
    video: Optional[UploadFile] = File(None),
    presentation: UploadFile = File(...),
    video_url: Optional[str] = Form(None),
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Accepts presentation and video (file or URL), creates lecture record,
    extracts slides, and starts background processing.
    Returns lecture ID.
    """
    if not video and not video_url:
        raise HTTPException(
            status_code=400,
            detail="Either video file or video URL must be provided"
        )

    logger.info(f"Received request: video file present={video is not None}, video_url={video_url}")

    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True) # Ensure uploads dir exists

    try:
        # Handle presentation file
        presentation_content = await presentation.read()
        file_extension = presentation.filename.split('.')[-1].lower()

        # Handle video input (save file or use URL)
        if video:
            video_filename = f"{uuid.uuid4()}_{video.filename}"
            video_path_obj = upload_dir / video_filename
            async with aiofiles.open(video_path_obj, 'wb') as out_file:
                content = await video.read()
                await out_file.write(content)
            video_path_str = str(video_path_obj)
        elif video_url:
            video_path_str = video_url
        else:
             # This case is already handled by the initial validation, but added for safety
             raise HTTPException(status_code=400, detail="No video source provided")

        # Create initial lecture record
        lecture = Lecture(
            title=presentation.filename,
            status="processing",
            video_path=video_path_str
        )
        db.add(lecture)
        db.flush() # Get the lecture ID generated by the DB
        lecture_id = lecture.id
        logger.info(f"Created Lecture record with ID: {lecture_id}")

        # Process presentation slides
        slide_images = await presentation_service.process_presentation(
            presentation_content,
            file_extension
        )

        # Save slides to DB
        for index, image_data in enumerate(slide_images):
            slide = Slide(
                lecture_id=lecture_id,
                index=index,
                image_data=image_data # Assuming this is already base64 encoded by the service
            )
            db.add(slide)
        logger.info(f"Saved {len(slide_images)} slides for lecture ID: {lecture_id}")

        # Enqueue background task for video processing
        background_tasks.add_task(
            process_video_background,
            video_path_str,
            lecture_id,
            db
        )

        db.commit() # Commit lecture and slides together

        return {"message": "Processing started", "lecture_id": lecture_id}

    except Exception as e:
        db.rollback() # Ensure rollback on any exception during setup
        logger.error(f"Error processing upload for lecture '{presentation.filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing files: {str(e)}"
        )


async def process_video_background(
    video_path_or_url: str,
    lecture_id: int,
    db: Session
):
    """
    Background task: Extracts audio, transcribes, matches to slides, saves results.
    Handles status updates and cleanup.
    """
    audio_path = None
    video_file_to_delete = None
    try:
        # 1. Update status & Extract/Download Audio
        _update_lecture_status(db, lecture_id, "downloading")
        if not video_path_or_url.startswith(('http://', 'https://')):
            logger.info(f"Processing local video file: {video_path_or_url}")
            audio_path = await transcription_service.extract_audio(video_path_or_url)
            video_file_to_delete = video_path_or_url # Mark local video file for deletion
        else:
            logger.info(f"Processing video from URL: {video_path_or_url}")
            audio_path = await transcription_service.download_and_extract_audio(video_path_or_url)
            # Don't delete the original URL input

        logger.info(f"Audio path: {audio_path}")
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file creation failed or file not found: {audio_path}")

        # 2. Update status & Transcribe
        _update_lecture_status(db, lecture_id, "transcribing")
        logger.info(f"Starting transcription for lecture {lecture_id}...")
        transcription = await transcription_service.transcribe(audio_path)
        logger.info(f"Transcription completed for lecture {lecture_id}")

        # 3. Update status & Match Slides
        _update_lecture_status(db, lecture_id, "matching")
        logger.info(f"Starting slide matching for lecture {lecture_id}...")
        slides = db.query(Slide).filter(Slide.lecture_id == lecture_id).order_by(Slide.index).all()

        # Prepare data for matching service
        slides_data = [{'image_data': slide.image_data, 'index': slide.index} for slide in slides]
        transcription_data = [
            {'start_time': seg['start_time'], 'end_time': seg['end_time'], 'text': seg['text'], 'confidence': seg.get('confidence', 1.0)}
            for seg in transcription.get('segments', [])
        ]

        matched_segments = await slide_matching_service.match_transcription_to_slides(
            video_path_or_url,
            slides_data,
            transcription_data
        )
        logger.info(f"Slide matching completed for lecture {lecture_id}")

        # 4. Save Matched Segments & Update status to Completed
        for segment_data in matched_segments:
            db_segment = TranscriptionSegment(
                lecture_id=lecture_id,
                start_time=segment_data['start_time'],
                end_time=segment_data['end_time'],
                text=segment_data['text'],
                confidence=segment_data.get('confidence', 1.0), # Use get with default
                slide_index=segment_data['slide_index']
            )
            db.add(db_segment)

        # Update status last after successfully adding segments
        _update_lecture_status(db, lecture_id, "completed")
        # The commit for segments happens within the final _update_lecture_status call

    except Exception as e:
        logger.error(f"Error processing video background task for lecture {lecture_id}: {e}", exc_info=True)
        # Attempt to set status to failed, rollback handled in helper/main block
        try:
            _update_lecture_status(db, lecture_id, "failed")
        except Exception as status_update_err:
             logger.error(f"Additionally failed to update status to 'failed' for lecture {lecture_id}: {status_update_err}")
        # No need to explicitly rollback here if _update_lecture_status handles it
        # db.rollback() # Rollback might be handled by the helper or context
        # Re-raising might not be useful unless something monitors background task exceptions
        # raise

    finally:
        # 5. Cleanup
        if audio_path:
            try:
                await transcription_service.cleanup(audio_path)
                logger.info(f"Cleaned up audio file: {audio_path}")
            except Exception as cleanup_err:
                logger.error(f"Error cleaning up audio file {audio_path}: {cleanup_err}")
        if video_file_to_delete:
            try:
                if os.path.exists(video_file_to_delete):
                    os.remove(video_file_to_delete)
                    logger.info(f"Cleaned up video file: {video_file_to_delete}")
            except Exception as cleanup_err:
                 logger.error(f"Error cleaning up video file {video_file_to_delete}: {cleanup_err}")


@router.get("/lectures/{lecture_id}/transcription")
async def get_lecture_transcription(
    lecture_id: int,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Retrieve complete lecture data including metadata, slides, and transcription segments.
    """
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    try:
        slides = db.query(Slide)\
            .filter(Slide.lecture_id == lecture_id)\
            .order_by(Slide.index)\
            .all()

        segments = db.query(TranscriptionSegment)\
            .filter(TranscriptionSegment.lecture_id == lecture_id)\
            .order_by(TranscriptionSegment.start_time)\
            .all()

        # Format data for API response
        formatted_slides = [
            {"imageUrl": slide.image_data, "index": slide.index} # Assuming image_data is base64
            for slide in slides
        ]
        formatted_segments = [
            {
                "id": segment.id,
                "startTime": segment.start_time,
                "endTime": segment.end_time,
                "text": segment.text,
                "confidence": segment.confidence,
                "slideIndex": segment.slide_index
            }
            for segment in segments
        ]

        return {
            "lecture_id": lecture.id, # Use lecture.id for consistency
            "title": lecture.title,
            "status": lecture.status,
            "slides": formatted_slides,
            "transcription": formatted_segments
        }

    except Exception as e:
        logger.error(f"Error retrieving lecture data for ID {lecture_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving lecture data: {str(e)}"
        )