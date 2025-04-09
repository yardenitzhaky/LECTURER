# app/api/api.py
import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

import aiofiles
from fastapi import (
    APIRouter, Form, UploadFile, File, HTTPException,
    BackgroundTasks, Depends
)
from sqlalchemy.orm import Session

from app import deps
from app.core.config import settings
from app.db.models import Lecture, TranscriptionSegment, Slide
from app.db.session import SessionLocal
from app.services.presentation import PresentationService
from app.services.slide_matching import SlideMatchingService
from app.services.summarization import SummarizationService # Import the class
from app.services.transcription import TranscriptionService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services directly in this module
transcription_service = TranscriptionService()
presentation_service = PresentationService()
slide_matching_service = SlideMatchingService()
summarization_service = SummarizationService() 

# --- Helper Function ---
def _update_lecture_status(db: Session, lecture_id: int, status: str):
    """Helper function to update lecture status, uses row locking."""
    try:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).with_for_update().first()
        if lecture:
            lecture.status = status
            db.commit()
            logger.info(f"Lecture ID {lecture_id} status updated to: {status}")
        else:
            logger.warning(f"Attempted status update for non-existent lecture ID: {lecture_id}")
    except Exception as e:
        logger.error(f"Failed to update status for lecture {lecture_id} to {status}: {e}", exc_info=True)
        try: db.rollback()
        except Exception as rb_exc: logger.error(f"Rollback failed during status update failure for lecture {lecture_id}: {rb_exc}", exc_info=True)
        raise # Re-raise original error

# --- API Endpoints ---

@router.post("/transcribe/", status_code=202) # Use 202 Accepted for background tasks
async def transcribe_lecture(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
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
        lecture = Lecture(title=lecture_title, status="pending", video_path=video_path_str)
        db.add(lecture)
        db.flush()
        lecture_id = lecture.id
        logger.info(f"Created Lecture record ID: {lecture_id}, Status: pending")

        # Process and save slides
        _update_lecture_status(db, lecture_id, "processing_slides")
        try:
            slide_images = await presentation_service.process_presentation(presentation_content, file_extension)
            slides_to_add = [Slide(lecture_id=lecture_id, index=i, image_data=img) for i, img in enumerate(slide_images)]
            if slides_to_add: db.add_all(slides_to_add)
            db.commit() # Commit lecture creation and slides together
            logger.info(f"Saved {len(slides_to_add)} slides for lecture ID: {lecture_id}")
        except Exception as pres_err:
             _update_lecture_status(db, lecture_id, "failed") # Mark as failed
             raise HTTPException(status_code=500, detail=f"Error processing presentation: {pres_err}") from pres_err

        # Enqueue background task
        background_tasks.add_task(process_video_background, video_path_or_url=video_path_str, lecture_id=lecture_id, db_session_factory=SessionLocal)
        _update_lecture_status(db, lecture_id, "processing") # Mark as processing now

        return {"message": "Processing started", "lecture_id": lecture_id}

    except Exception as e:
        logger.error(f"Error in /transcribe/ (Lecture ID: {lecture_id or 'N/A'}): {e}", exc_info=True)
        if lecture_id and not isinstance(e, HTTPException): # Avoid double update if already failed
             try: _update_lecture_status(db, lecture_id, "failed")
             except Exception as status_err: logger.error(f"Failed to mark lecture {lecture_id} as failed during error handling: {status_err}")
        elif not lecture_id: db.rollback() # Rollback if lecture wasn't created

        # Re-raise HTTPExceptions, wrap others
        if isinstance(e, HTTPException): raise e
        else: raise HTTPException(status_code=500, detail=f"Server error during upload: {str(e)}")


async def process_video_background(
    video_path_or_url: str,
    lecture_id: int,
    db_session_factory: Callable[[], Session]
):
    """Background task: audio extraction, transcription, slide matching, saving."""
    audio_path: Optional[str] = None
    video_file_to_delete: Optional[str] = video_path_or_url if not video_path_or_url.startswith(('http://', 'https://')) else None
    db: Optional[Session] = None

    def update_status(status: str):
        """Nested helper to update status using the task's DB session."""
        if not db: return
        try: _update_lecture_status(db, lecture_id, status)
        except Exception as e: logger.error(f"[BG Task Helper] Status update failed for L:{lecture_id} S:{status}: {e}")

    try:
        db = db_session_factory()
        logger.info(f"[BG Task {lecture_id}] Started.")

        # 1. Audio Handling
        update_status("downloading")
        if video_file_to_delete:
            if not os.path.exists(video_path_or_url): raise FileNotFoundError(f"Video file missing: {video_path_or_url}")
            audio_path = await transcription_service.extract_audio(video_path_or_url)
        else:
            audio_path = await transcription_service.download_and_extract_audio(video_path_or_url)
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio processing failed: {audio_path}")
        logger.info(f"[BG Task {lecture_id}] Audio ready: {audio_path}")

        # 2. Transcription
        update_status("transcribing")
        transcription_result = await transcription_service.transcribe(audio_path)
        if not transcription_result or 'segments' not in transcription_result:
            raise ValueError("Invalid transcription result format.")
        transcription_segments_raw = transcription_result['segments']
        logger.info(f"[BG Task {lecture_id}] Transcription found {len(transcription_segments_raw)} segments.")

        # 3. Slide Matching
        update_status("matching")
        slides = db.query(Slide).filter(Slide.lecture_id == lecture_id).order_by(Slide.index).all()
        if not slides: raise ValueError(f"No slides found in DB for lecture {lecture_id}.")
        slides_data = [{'image_data': s.image_data, 'index': s.index} for s in slides]
        transcription_data = [
            {'start_time': seg['start_time'], 'end_time': seg['end_time'], 'text': seg['text'], 'confidence': seg.get('confidence', 1.0)}
            for seg in transcription_segments_raw if seg.get('start_time') is not None
        ]
        matched_segments_data = await slide_matching_service.match_transcription_to_slides(
            video_path_or_url, slides_data, transcription_data
        )
        logger.info(f"[BG Task {lecture_id}] Matching complete ({len(matched_segments_data)} segments).")

        # 4. Save Segments
        update_status("saving_segments")
        db.query(TranscriptionSegment).filter(TranscriptionSegment.lecture_id == lecture_id).delete()
        db.flush()
        segments_to_add = [
            TranscriptionSegment(
                lecture_id=lecture_id, start_time=seg['start_time'], end_time=seg['end_time'],
                text=seg.get('text', ''), confidence=seg.get('confidence', 1.0), slide_index=seg['slide_index']
            ) for seg in matched_segments_data if seg.get('slide_index') is not None
        ]
        if segments_to_add:
            db.add_all(segments_to_add)
            logger.info(f"[BG Task {lecture_id}] Saving {len(segments_to_add)} segments.")
        else:
             logger.warning(f"[BG Task {lecture_id}] No valid segments to save after matching.")
        db.commit()

        # 5. Mark Complete
        update_status("completed")
        logger.info(f"[BG Task {lecture_id}] Completed successfully.")

    except (FileNotFoundError, ValueError) as specific_err:
        logger.error(f"[BG Task {lecture_id}] Failed: {specific_err}", exc_info=True)
        if db: update_status("failed")
    except Exception as e:
        logger.error(f"[BG Task {lecture_id}] Unexpected error: {e}", exc_info=True)
        if db:
            try: update_status("failed")
            except Exception: logger.error(f"[BG Task {lecture_id}] Also failed to mark as failed.")
            try: db.rollback()
            except Exception: logger.error(f"[BG Task {lecture_id}] Rollback failed during error handling.")
    finally:
        # 6. Cleanup
        logger.info(f"[BG Task {lecture_id}] Cleaning up resources.")
        if audio_path and os.path.exists(audio_path):
            try: await transcription_service.cleanup(audio_path)
            except Exception as cl_err: logger.error(f"[BG Task {lecture_id}] Audio cleanup error: {cl_err}")
        if video_file_to_delete and os.path.exists(video_file_to_delete):
            try: os.remove(video_file_to_delete)
            except Exception as cl_err: logger.error(f"[BG Task {lecture_id}] Video cleanup error: {cl_err}")
        if db: db.close()


@router.get("/lectures/{lecture_id}/transcription")
async def get_lecture_transcription(
    lecture_id: int,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """Retrieve lecture data including metadata, slides, and transcription."""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
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
            "slides": [{"imageUrl": s.image_data, "index": s.index, "summary": s.summary} for s in slides],
            "transcription": [{
                "id": seg.id, "startTime": seg.start_time, "endTime": seg.end_time,
                "text": seg.text, "confidence": seg.confidence, "slideIndex": seg.slide_index
             } for seg in segments]
        }
    except Exception as e:
        logger.error(f"Error retrieving data for lecture {lecture_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving lecture data: {str(e)}")


@router.post("/lectures/{lecture_id}/slides/{slide_index}/summarize")
async def summarize_slide_endpoint(
    lecture_id: int,
    slide_index: int,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Optional[str]]:
    """Generates and saves a summary for a specific slide."""
    logger.info(f"Summarize request for L:{lecture_id} S:{slide_index}")

    slide = db.query(Slide).filter(Slide.lecture_id == lecture_id, Slide.index == slide_index).with_for_update().first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    lecture_status = db.query(Lecture.status).filter(Lecture.id == lecture_id).scalar()
    if lecture_status != 'completed':
         raise HTTPException(status_code=400, detail=f"Cannot summarize, lecture status is '{lecture_status}'.")

    segments = db.query(TranscriptionSegment).filter(
        TranscriptionSegment.lecture_id == lecture_id,
        TranscriptionSegment.slide_index == slide_index
    ).order_by(TranscriptionSegment.start_time).all()

    full_slide_text = " ".join([seg.text for seg in segments if seg.text]).strip()

    if not full_slide_text:
        logger.warning(f"No text to summarize for L:{lecture_id} S:{slide_index}")
        return {"summary": None, "message": "No transcription text available for this slide."}

    if not summarization_service.client:
         logger.error("Summarization service unavailable (likely no API key)")
         raise HTTPException(status_code=503, detail="Summarization service is not configured.")

    try:
        new_summary = await summarization_service.summarize_text(full_slide_text)
        if new_summary is None:
            logger.error(f"Summarization returned None for L:{lecture_id} S:{slide_index}")
            raise HTTPException(status_code=503, detail="Summarization service returned no content.")

        slide.summary = new_summary
        db.add(slide)
        db.commit()
        logger.info(f"Summary saved for L:{lecture_id} S:{slide_index}")
        return {"summary": new_summary}
    except HTTPException as http_exc:
         raise http_exc # Re-raise exceptions from the service or prior checks
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to summarize or save summary for L:{lecture_id} S:{slide_index}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during summarization process: {str(e)}")