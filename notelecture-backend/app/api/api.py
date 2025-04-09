# app/api/api.py
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os
from pathlib import Path
import aiofiles
import uuid
import base64
import io # Keep io for potential future use

from app.services.transcription import TranscriptionService
from app.services.presentation import PresentationService
from app.services.slide_matching import SlideMatchingService
from app.services.summarization import summarization_service # Import the new service
from app.db.models import Lecture, TranscriptionSegment, Slide
from app import deps
from app.db.session import SessionLocal  # Import SessionLocal
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
transcription_service = TranscriptionService()
presentation_service = PresentationService()
slide_matching_service = SlideMatchingService()
# summarization_service is already instantiated in its module

# --- Helper Function ---
def _update_lecture_status(db: Session, lecture_id: int, status: str):
    """Helper function to update lecture status in the database."""
    lecture = None # Initialize lecture to None
    try:
        # Use with_for_update to lock the row during update
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).with_for_update().first()
        if lecture:
            lecture.status = status
            db.commit() # Commit the change
            logger.info(f"Lecture ID {lecture_id} status updated to: {status}")
        else:
            logger.warning(f"Attempted to update status for non-existent lecture ID: {lecture_id}")
            # Don't rollback here, as the record might not exist, which isn't necessarily an error in all contexts
    except Exception as e:
        logger.error(f"Failed to update status for lecture {lecture_id} to {status}: {e}", exc_info=True)
        try:
            db.rollback() # Attempt rollback on error during status update
            logger.info(f"Rolled back transaction for lecture {lecture_id} due to status update failure.")
        except Exception as rb_exc:
            logger.error(f"Failed to rollback transaction for lecture {lecture_id}: {rb_exc}", exc_info=True)
        raise # Re-raise the original exception after attempting rollback


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
    extracts slides, and starts background processing (transcription & matching).
    Summarization is now on-demand. Returns lecture ID.
    """
    if not video and not video_url:
        raise HTTPException(
            status_code=400,
            detail="Either video file or video URL must be provided"
        )

    if video_url:
        logger.info(f"Received request with video_url: {video_url[:100]}...")
    else:
        logger.info(f"Received request with video file: {video.filename if video else 'None'}")

    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    lecture_id = None

    try:
        # Handle presentation file
        presentation_content = await presentation.read()
        file_extension = presentation.filename.split('.')[-1].lower()

        # Handle video input (save file or use URL)
        video_path_str: str
        if video:
            video_filename = f"{uuid.uuid4()}_{video.filename}"
            video_path_obj = upload_dir / video_filename
            async with aiofiles.open(video_path_obj, 'wb') as out_file:
                content = await video.read()
                await out_file.write(content)
            video_path_str = str(video_path_obj)
            logger.info(f"Saved uploaded video to: {video_path_str}")
        elif video_url:
            video_path_str = video_url
            logger.info(f"Using video URL: {video_path_str}")
        else:
             raise HTTPException(status_code=400, detail="No video source provided")

        # Create initial lecture record
        lecture = Lecture(
            title=presentation.filename or "Untitled Lecture",
            status="pending",
            video_path=video_path_str
        )
        db.add(lecture)
        db.flush()
        lecture_id = lecture.id
        logger.info(f"Created Lecture record with ID: {lecture_id}, status: {lecture.status}")

        # Process presentation slides
        _update_lecture_status(db, lecture_id, "processing_slides")
        slide_images = await presentation_service.process_presentation(
            presentation_content,
            file_extension
        )

        # Save slides to DB
        for index, image_data in enumerate(slide_images):
            slide = Slide(
                lecture_id=lecture_id,
                index=index,
                image_data=image_data
            )
            db.add(slide)
        db.commit()
        logger.info(f"Saved {len(slide_images)} slides for lecture ID: {lecture_id}")

        # Enqueue background task
        background_tasks.add_task(
            process_video_background, # Pass the function itself
            video_path_str,
            lecture_id,
            db_session_factory=SessionLocal # Pass the session factory
        )

        # Update status to indicate processing has started
        _update_lecture_status(db, lecture_id, "processing")

        return {"message": "Processing started", "lecture_id": lecture_id}

    except Exception as e:
        if lecture_id:
            logger.error(f"Error during initial processing for lecture {lecture_id}: {e}", exc_info=True)
            try: _update_lecture_status(db, lecture_id, "failed")
            except Exception as status_err: logger.error(f"Failed to mark lecture {lecture_id} as failed: {status_err}")
        else:
            logger.error(f"Error processing upload before lecture creation: {e}", exc_info=True)
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")


async def process_video_background(
    video_path_or_url: str,
    lecture_id: int,
    db_session_factory: callable # Accept the session factory
):
    """
    Background task: Extracts audio, transcribes, matches slides, saves segments.
    Summarization is NOT done here anymore. Uses a dedicated DB session.
    """
    audio_path: Optional[str] = None
    video_file_to_delete: Optional[str] = None
    db: Session = db_session_factory() # Create a new session for this task

    def update_status(status: str):
        """Local helper to update status using the task's session."""
        nonlocal db
        try:
            lecture = db.query(Lecture).filter(Lecture.id == lecture_id).with_for_update().first()
            if lecture:
                lecture.status = status
                db.commit()
                logger.info(f"Lecture ID {lecture_id} status updated to: {status}")
            else:
                 logger.warning(f"Cannot update status: Lecture ID {lecture_id} not found in this session.")
        except Exception as e:
            logger.error(f"Failed to update status for lecture {lecture_id} to {status}: {e}", exc_info=True)
            try: db.rollback()
            except Exception as rb_err: logger.error(f"Rollback failed during status update error: {rb_err}")

    try:
        logger.info(f"Background task started for lecture ID: {lecture_id}")

        # 1. Update status & Extract/Download Audio
        update_status("downloading")
        if not video_path_or_url.startswith(('http://', 'https://')):
            logger.info(f"Processing local video file: {video_path_or_url}")
            if not os.path.exists(video_path_or_url):
                 raise FileNotFoundError(f"Local video file does not exist: {video_path_or_url}")
            audio_path = await transcription_service.extract_audio(video_path_or_url)
            video_file_to_delete = video_path_or_url
        else:
            logger.info(f"Processing video from URL: {video_path_or_url}")
            audio_path = await transcription_service.download_and_extract_audio(video_path_or_url)

        logger.info(f"Audio extracted/downloaded to path: {audio_path}")
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file creation failed or file not found: {audio_path}")

        # 2. Update status & Transcribe
        update_status("transcribing")
        logger.info(f"Starting transcription for lecture {lecture_id}...")
        transcription = await transcription_service.transcribe(audio_path)
        if not transcription or 'segments' not in transcription:
             raise ValueError("Transcription service did not return valid segments.")
        logger.info(f"Transcription completed for lecture {lecture_id}. Segments found: {len(transcription.get('segments', []))}")

        # 3. Update status & Match Slides
        update_status("matching")
        logger.info(f"Starting slide matching for lecture {lecture_id}...")
        slides = db.query(Slide).filter(Slide.lecture_id == lecture_id).order_by(Slide.index).all()
        if not slides:
            raise ValueError(f"No slides found for lecture {lecture_id} in the database.")

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
        logger.info(f"Slide matching completed for lecture {lecture_id}. Segments matched: {len(matched_segments)}")

        # 4. Save Matched Segments
        update_status("saving_segments")
        db.query(TranscriptionSegment).filter(TranscriptionSegment.lecture_id == lecture_id).delete()
        db.flush()
        for segment_data in matched_segments:
            db_segment = TranscriptionSegment(
                lecture_id=lecture_id,
                start_time=segment_data['start_time'],
                end_time=segment_data['end_time'],
                text=segment_data['text'],
                confidence=segment_data.get('confidence', 1.0),
                slide_index=segment_data['slide_index']
            )
            db.add(db_segment)
        db.commit()
        logger.info(f"Saved {len(matched_segments)} transcription segments for lecture {lecture_id}")

        # ---- SUMMARIZATION STEP IS REMOVED FROM HERE ----

        # 5. Final Status Update to Completed
        update_status("completed")
        logger.info(f"Background processing (excluding summarization) completed for lecture ID: {lecture_id}")

    except FileNotFoundError as fnf_err:
        logger.error(f"[BG Task {lecture_id}] File not found error: {fnf_err}", exc_info=True)
        try: update_status("failed")
        except Exception as status_err: logger.error(f"Failed to update status to 'failed': {status_err}")
    except ValueError as val_err:
        logger.error(f"[BG Task {lecture_id}] Value error: {val_err}", exc_info=True)
        try: update_status("failed")
        except Exception as status_err: logger.error(f"Failed to update status to 'failed': {status_err}")
    except Exception as e:
        logger.error(f"[BG Task {lecture_id}] Unhandled error: {e}", exc_info=True)
        try: update_status("failed")
        except Exception as status_update_err: logger.error(f"Additionally failed to update status to 'failed': {status_update_err}")

    finally:
        # 6. Cleanup
        logger.info(f"Starting cleanup for lecture {lecture_id}")
        if audio_path:
            try: await transcription_service.cleanup(audio_path)
            except Exception as cleanup_err: logger.error(f"Error cleaning up audio file {audio_path}: {cleanup_err}")
        if video_file_to_delete:
            try:
                if os.path.exists(video_file_to_delete): os.remove(video_file_to_delete)
            except Exception as cleanup_err: logger.error(f"Error cleaning up video file {video_file_to_delete}: {cleanup_err}")
        if db: db.close()
        logger.info(f"Database session closed for background task of lecture {lecture_id}")


@router.get("/lectures/{lecture_id}/transcription")
async def get_lecture_transcription(
    lecture_id: int,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Retrieve complete lecture data including metadata, slides (with summaries),
    and transcription segments.
    """
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    logger.info(f"Fetching data for lecture {lecture_id}, current status: {lecture.status}")

    try:
        slides = db.query(Slide)\
            .filter(Slide.lecture_id == lecture_id)\
            .order_by(Slide.index)\
            .all()
        segments = db.query(TranscriptionSegment)\
            .filter(TranscriptionSegment.lecture_id == lecture_id)\
            .order_by(TranscriptionSegment.start_time)\
            .all()

        formatted_slides = [
            {"imageUrl": slide.image_data, "index": slide.index, "summary": slide.summary}
            for slide in slides
        ]
        formatted_segments = [
            {"id": seg.id, "startTime": seg.start_time, "endTime": seg.end_time, "text": seg.text, "confidence": seg.confidence, "slideIndex": seg.slide_index}
            for seg in segments
        ]

        response_data = {
            "lecture_id": lecture.id, "title": lecture.title, "status": lecture.status,
            "slides": formatted_slides, "transcription": formatted_segments
        }
        logger.info(f"Successfully retrieved data for lecture {lecture_id}")
        return response_data

    except Exception as e:
        logger.error(f"Error retrieving lecture data for ID {lecture_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error retrieving lecture data: {str(e)}")


@router.post("/lectures/{lecture_id}/slides/{slide_index}/summarize", response_model=Dict[str, Optional[str]])
async def summarize_slide_endpoint(
    lecture_id: int,
    slide_index: int,
    db: Session = Depends(deps.get_db)
):
    """
    Generates and saves a summary for a specific slide based on its transcription text.
    Returns the generated summary.
    """
    logger.info(f"Received request to summarize slide {slide_index} for lecture {lecture_id}")

    # Fetch the slide and lock it for update
    slide = db.query(Slide).filter(
        Slide.lecture_id == lecture_id,
        Slide.index == slide_index
    ).with_for_update().first() # Added with_for_update

    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found for this lecture and index.")

    # --- Optional Check: Return existing summary if present ---
    # if slide.summary:
    #     logger.info(f"Summary already exists for slide {slide_index}, lecture {lecture_id}. Returning existing.")
    #     return {"summary": slide.summary}
    # --- End Optional Check ---

    # Fetch transcription segments for this specific slide
    segments = db.query(TranscriptionSegment).filter(
        TranscriptionSegment.lecture_id == lecture_id,
        TranscriptionSegment.slide_index == slide_index
    ).order_by(TranscriptionSegment.start_time).all()

    if not segments:
        logger.warning(f"No transcription text found for slide {slide_index}, lecture {lecture_id}.")
        return {"summary": None, "message": "No transcription text available for this slide."}

    # Concatenate text
    full_slide_text = " ".join([seg.text for seg in segments if seg.text]).strip()

    if not full_slide_text:
         logger.warning(f"Concatenated transcription text is empty for slide {slide_index}, lecture {lecture_id}.")
         return {"summary": None, "message": "Transcription text is empty for this slide."}

    # Call summarization service
    logger.info(f"Requesting summarization for slide {slide_index}, lecture {lecture_id}")
    if not summarization_service.client:
         logger.error("Summarization service client not initialized (OpenAI key likely missing).")
         raise HTTPException(status_code=503, detail="Summarization service is not configured.")

    new_summary = await summarization_service.summarize_text(full_slide_text)

    if new_summary is None:
        logger.error(f"Summarization failed for slide {slide_index}, lecture {lecture_id} (service returned None).")
        raise HTTPException(status_code=503, detail="Failed to generate summary. The summarization service may be unavailable or encountered an error.")

    # Update slide record and commit
    try:
        slide.summary = new_summary
        db.add(slide) # Add slide back to session (needed if fetched then modified)
        db.commit()
        # db.refresh(slide) # Optional: Refresh to get committed state if needed later in this request
        logger.info(f"Successfully generated and saved summary for slide {slide_index}, lecture {lecture_id}")
        return {"summary": new_summary}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save summary to DB for slide {slide_index}, lecture {lecture_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save the generated summary to the database.")