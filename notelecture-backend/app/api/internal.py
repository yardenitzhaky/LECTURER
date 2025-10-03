# app/api/internal.py
"""
Internal API endpoints for communication between external service and main backend.
These endpoints are called by the Cloud Run external service.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from app.utils.common import get_db
from app.db.models import Lecture, TranscriptionSegment
from app.services.transcription import TranscriptionService
from app.utils.database import update_lecture_status
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

transcription_service = TranscriptionService()


@router.post("/transcribe-audio")
async def transcribe_audio_internal(
    data: Dict[str, Any],
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Internal endpoint to transcribe base64 audio data.
    Called by external service.
    """
    try:
        # Optional: Add API key validation here
        # if authorization != f"Bearer {settings.INTERNAL_API_KEY}":
        #     raise HTTPException(status_code=401, detail="Unauthorized")

        audio_base64 = data.get("audio_data")
        if not audio_base64:
            raise HTTPException(status_code=400, detail="audio_data is required")

        logger.info(f"Transcribing audio (base64 length: {len(audio_base64)} chars)")

        # Decode base64 and save to temp file
        import base64
        import tempfile
        import os

        audio_bytes = base64.b64decode(audio_base64)
        logger.info(f"Decoded audio: {len(audio_bytes)} bytes")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_bytes)
            audio_path = tmp_file.name

        logger.info(f"Saved audio to temp file: {audio_path}")

        # Transcribe
        result = await transcription_service.transcribe(audio_path)
        logger.info(f"Transcription complete: {len(result.get('segments', []))} segments")

        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Cleaned up temp file: {audio_path}")

        return result

    except Exception as e:
        logger.error(f"Error in transcribe_audio_internal: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete-lecture-processing")
async def complete_lecture_processing(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Internal endpoint to receive completed lecture processing results.
    Called by external service when processing is done.
    """
    try:
        # Optional: Add API key validation
        # if authorization != f"Bearer {settings.INTERNAL_API_KEY}":
        #     raise HTTPException(status_code=401, detail="Unauthorized")

        lecture_id = data.get("lecture_id")
        status = data.get("status")
        segments = data.get("segments", [])
        error = data.get("error")

        if not lecture_id:
            raise HTTPException(status_code=400, detail="lecture_id is required")

        logger.info(f"Receiving completion for lecture {lecture_id}: status={status}, segments={len(segments)}")

        if status == "completed" and segments:
            # Save segments to database
            logger.info(f"Deleting existing segments for lecture {lecture_id}")
            db.query(TranscriptionSegment).filter(
                TranscriptionSegment.lecture_id == lecture_id
            ).delete()

            segments_to_add = [
                TranscriptionSegment(
                    lecture_id=lecture_id,
                    start_time=seg.get("start_time"),
                    end_time=seg.get("end_time"),
                    text=seg.get("text", ""),
                    confidence=seg.get("confidence", 1.0),
                    slide_index=seg.get("slide_index", 0)
                )
                for seg in segments
            ]

            if segments_to_add:
                db.add_all(segments_to_add)
                logger.info(f"Adding {len(segments_to_add)} segments to database")

            update_lecture_status(db, lecture_id, "completed")
            db.commit()

            logger.info(f"Lecture {lecture_id} completed successfully: saved {len(segments_to_add)} segments")

        elif status == "failed":
            update_lecture_status(db, lecture_id, "failed")
            db.commit()
            logger.error(f"Lecture {lecture_id} failed: {error}")

        return {"status": "success", "lecture_id": lecture_id}

    except Exception as e:
        logger.error(f"Error in complete_lecture_processing: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
