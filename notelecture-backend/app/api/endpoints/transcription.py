# app/api/endpoints/transcription.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi import Depends
from typing import Dict, Any
import os
import aiofiles
from app.services.transcription import TranscriptionService
from app.db import models
from app.api import deps

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
        lecture = models.Lecture(
            title=file.filename,
            status="completed"
        )
        db.add(lecture)
        db.flush()

        # Add transcription segments
        for segment in transcription["segments"]:
            db_segment = models.TranscriptionSegment(
                lecture_id=lecture.id,
                start_time=segment["start_time"],
                end_time=segment["end_time"],
                text=segment["text"],
                confidence=segment["confidence"]
            )
            db.add(db_segment)
            db.flush()

            # Add words
            for word in segment["words"]:
                db_word = models.Word(
                    segment_id=db_segment.id,
                    text=word["text"],
                    start_time=word["start_time"],
                    end_time=word["end_time"],
                    confidence=word["confidence"]
                )
                db.add(db_word)

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

@router.get("/lectures/{lecture_id}/transcription")
async def get_lecture_transcription(
    lecture_id: int,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Retrieve the transcription for a specific lecture.
    """
    try:
        # Get all segments for the lecture
        segments = db.query(models.TranscriptionSegment)\
            .filter(models.TranscriptionSegment.lecture_id == lecture_id)\
            .all()

        if not segments:
            raise HTTPException(status_code=404, detail="Transcription not found")

        # Get words for each segment
        result = []
        for segment in segments:
            words = db.query(models.Word)\
                .filter(models.Word.segment_id == segment.id)\
                .all()

            result.append({
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text,
                "confidence": segment.confidence,
                "words": [
                    {
                        "text": word.text,
                        "start_time": word.start_time,
                        "end_time": word.end_time,
                        "confidence": word.confidence
                    }
                    for word in words
                ]
            })

        return {
            "lecture_id": lecture_id,
            "segments": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving transcription: {str(e)}"
        )