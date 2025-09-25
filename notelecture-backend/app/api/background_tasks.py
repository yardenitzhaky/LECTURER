# app/api/background_tasks.py
import os
import logging
from typing import Optional, Callable
from sqlalchemy.orm import Session

from app.db.models import Slide, TranscriptionSegment
from app.services.transcription import TranscriptionService
from app.services.slide_matching import SlideMatchingService
from app.utils.database import update_lecture_status

logger = logging.getLogger(__name__)

# Initialize services
transcription_service = TranscriptionService()
slide_matching_service = SlideMatchingService()


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
        if not db:
            return
        try:
            update_lecture_status(db, lecture_id, status)
        except Exception as e:
            logger.error(f"[BG Task Helper] Status update failed for L:{lecture_id} S:{status}: {e}")

    try:
        db = db_session_factory()
        logger.info(f"[BG Task {lecture_id}] Started.")

        # 1. Audio Handling
        update_status("downloading")
        if video_file_to_delete:
            logger.info(f"[BG Task {lecture_id}] Processing local video file: {video_path_or_url}")
            if not os.path.exists(video_path_or_url):
                raise FileNotFoundError(f"Video file missing: {video_path_or_url}")
            audio_path = await transcription_service.extract_audio(video_path_or_url)
        else:
            logger.info(f"[BG Task {lecture_id}] Processing video URL: {video_path_or_url}")
            audio_path = await transcription_service.download_and_extract_audio(video_path_or_url)

        if not audio_path or not os.path.exists(audio_path):
            logger.error(f"[BG Task {lecture_id}] Audio processing failed - file not found: {audio_path}")
            logger.error(f"[BG Task {lecture_id}] Checking if file exists: {os.path.exists(audio_path) if audio_path else 'None'}")
            raise FileNotFoundError(f"Audio processing failed: {audio_path}")
        logger.info(f"[BG Task {lecture_id}] Audio ready: {audio_path} (size: {os.path.getsize(audio_path)} bytes)")

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
        if not slides:
            raise ValueError(f"No slides found in DB for lecture {lecture_id}.")
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
        if db:
            update_status("failed")
    except Exception as e:
        logger.error(f"[BG Task {lecture_id}] Unexpected error: {e}", exc_info=True)
        if db:
            try:
                update_status("failed")
            except Exception:
                logger.error(f"[BG Task {lecture_id}] Also failed to mark as failed.")
            try:
                db.rollback()
            except Exception:
                logger.error(f"[BG Task {lecture_id}] Rollback failed during error handling.")
    finally:
        # 6. Cleanup
        logger.info(f"[BG Task {lecture_id}] Cleaning up resources.")
        if audio_path and os.path.exists(audio_path):
            try:
                await transcription_service.cleanup(audio_path)
            except Exception as cl_err:
                logger.error(f"[BG Task {lecture_id}] Audio cleanup error: {cl_err}")
        if video_file_to_delete and os.path.exists(video_file_to_delete):
            try:
                os.remove(video_file_to_delete)
            except Exception as cl_err:
                logger.error(f"[BG Task {lecture_id}] Video cleanup error: {cl_err}")
        if db:
            db.close()