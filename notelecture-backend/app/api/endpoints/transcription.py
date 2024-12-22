# app/api/endpoints/transcription.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi import Depends
from typing import Dict, Any
import os
from pathlib import Path
import aiofiles
from app.services.transcription import TranscriptionService
from app.db.models import Lecture, TranscriptionSegment
from app.api import deps
import logging
logger = logging.getLogger(__name__)


router = APIRouter()
transcription_service = TranscriptionService()

@router.post("/transcribe/")
async def transcribe_lecture(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Upload a video file and transcribe it.
    Returns the transcription with word-level timestamps.
    """
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_path = upload_dir / file.filename
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # Extract audio
        audio_path = await transcription_service.extract_audio(str(file_path))

        # Transcribe
        transcription = await transcription_service.transcribe(audio_path)

        # Store in database
        lecture = Lecture(
            title=file.filename,
            status="completed"
        )
        db.add(lecture)
        db.flush()

        # Add transcription segments
        for segment in transcription["segments"]:
            db_segment = TranscriptionSegment(
                lecture_id=lecture.id,
                start_time=segment["start_time"],
                end_time=segment["end_time"],
                text=segment["text"],
                confidence=segment["confidence"]
            )
            db.add(db_segment)
            db.flush()

        db.commit()

        # Clean up files in background
        background_tasks.add_task(transcription_service.cleanup, audio_path)
        background_tasks.add_task(os.remove, file_path)

        return {
            "message": "Transcription completed successfully",
            "lecture_id": lecture.id,
            "transcription": transcription
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing video: {str(e)}"
        )

# app/api/endpoints/transcription.py
@router.get("/lectures/{lecture_id}/transcription")
async def get_lecture_transcription(
    lecture_id: int,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Retrieve the transcription for a specific lecture.
    """
    try:
        # Get lecture info first
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if not lecture:
            raise HTTPException(status_code=404, detail="Lecture not found")

        # Get all segments for the lecture
        segments = db.query(TranscriptionSegment)\
            .filter(TranscriptionSegment.lecture_id == lecture_id)\
            .all()

        if not segments:
            raise HTTPException(status_code=404, detail="Transcription not found")

        # Match the frontend expected format
        result = []
        for segment in segments:
            result.append({
                "id": segment.id,
                "startTime": segment.start_time,
                "endTime": segment.end_time,
                "text": segment.text,
                "confidence": segment.confidence
            })

        return {
            "lecture_id": lecture_id,
            "title": lecture.title,
            "status": lecture.status,
            "transcription": result,
            "slides": []  # Empty array for now
        }

    except Exception as e:
        logger.error(f"Error retrieving transcription: {str(e)}")  # Add logging
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving transcription: {str(e)}"
        )