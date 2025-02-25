# app/api/endpoints/transcription.py
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi import Depends
from typing import Dict, Any, Optional
import os
from pathlib import Path
import aiofiles
import uuid
import base64
import io
from app.services.transcription import TranscriptionService
from app.services.presentation import PresentationService
from app.services.slide_matching import SlideMatchingService
from app.db.models import Lecture, TranscriptionSegment, Slide
from app.api import deps
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

transcription_service = TranscriptionService()
presentation_service = PresentationService()
slide_matching_service = SlideMatchingService()

@router.post("/transcribe/")
async def transcribe_lecture(
    background_tasks: BackgroundTasks,
    video: Optional[UploadFile] = File(None),
    presentation: UploadFile = File(...),
    video_url: Optional[str] = Form(None),
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Upload video and presentation files and process them.
    """
    try:
        if not video and not video_url:
            raise HTTPException(
                status_code=400,
                detail="Either video file or video URL must be provided"
            )

        print(f"Received request: video={video is not None}, video_url={video_url}")

        # Create uploads directory if it doesn't exist (for video only)
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        # Read presentation content directly
        presentation_content = await presentation.read()
        file_extension = presentation.filename.split('.')[-1]

        # Process video
        if video:
            video_filename = f"{uuid.uuid4()}_{video.filename}"
            video_path = upload_dir / video_filename
            async with aiofiles.open(video_path, 'wb') as out_file:
                content = await video.read()
                await out_file.write(content)
        else:
            # Handle video URL case
            video_path = video_url

        # Create lecture record
        lecture = Lecture(
            title=presentation.filename,
            status="processing",
            video_path=str(video_path) if isinstance(video_path, Path) else video_path
        )
        db.add(lecture)
        db.flush()

        # Process presentation immediately
        slide_images = await presentation_service.process_presentation(
            presentation_content,
            file_extension
        )

        # Save slides to database with base64 data
        for index, image_data in enumerate(slide_images):
            slide = Slide(
                lecture_id=lecture.id,
                index=index,
                image_data=image_data
            )
            db.add(slide)

        # Process video in background
        background_tasks.add_task(
            process_video_background,
            video_path if isinstance(video_path, str) else str(video_path),
            lecture.id,
            db
        )

        db.commit()

        return {
            "message": "Processing started",
            "lecture_id": lecture.id
        }

    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing files: {str(e)}"
        )

# app/api/endpoints/transcription.py

async def process_video_background(
    video_path: str,
    lecture_id: int,
    db: Session
):
    """Background task to process video."""
    try:
        # Update status
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "downloading"
        db.commit()
        # Extract audio if it's a video file
        if not video_path.startswith('http'):
            logger.info(f"Processing local video file: {video_path}")
            audio_path = await transcription_service.extract_audio(video_path)
        else:
            # Handle YouTube/URL case
            logger.info(f"Processing video from URL: {video_path}")
            audio_path = await transcription_service.download_and_extract_audio(video_path)

        logger.info(f"Audio extraction completed. Audio path: {audio_path}")


        # Check if audio file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "transcribing"
        db.commit()
            
        # Transcribe
        logger.info("Starting transcription...")
        transcription = await transcription_service.transcribe(audio_path)
        logger.info("Transcription completed")

        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "matching"
        db.commit()

        # Get slides for the lecture
        slides = db.query(Slide).filter(Slide.lecture_id == lecture_id).order_by(Slide.index).all()
        
        # Prepare slides data for matching
        slides_data = [
            {
                'image_data': slide.image_data,
                'index': slide.index
            }
            for slide in slides
        ]

        # Match transcription segments to slides
        matched_segments = await slide_matching_service.match_transcription_to_slides(
            video_path,
            slides_data,
            [
                {
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'text': segment['text'],
                    'confidence': segment['confidence']
                }
                for segment in transcription['segments']
            ]
        )

        # Update lecture status
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "completed"
        
        # Add transcription segments with slide indices
        for segment in matched_segments:
            db_segment = TranscriptionSegment(
                lecture_id=lecture_id,
                start_time=segment['start_time'],
                end_time=segment['end_time'],
                text=segment['text'],
                confidence=segment['confidence'],
                slide_index=segment['slide_index']
            )
            db.add(db_segment)

        db.commit()

        # Cleanup
        await transcription_service.cleanup(audio_path)
        if not video_path.startswith('http'):
            os.remove(video_path)

    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        db.rollback()
        raise

@router.get("/lectures/{lecture_id}/transcription")
async def get_lecture_transcription(
    lecture_id: int,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Retrieve the transcription and slides for a specific lecture.
    """
    try:
        # Get lecture info
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if not lecture:
            raise HTTPException(status_code=404, detail="Lecture not found")

        # Get slides
        slides = db.query(Slide)\
            .filter(Slide.lecture_id == lecture_id)\
            .order_by(Slide.index)\
            .all()

        # Get transcription segments
        segments = db.query(TranscriptionSegment)\
            .filter(TranscriptionSegment.lecture_id == lecture_id)\
            .order_by(TranscriptionSegment.start_time)\
            .all()

        # Format response
        formatted_slides = [
            {
                "imageUrl": slide.image_data,  # Now using base64 data directly
                "index": slide.index
            }
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
            "lecture_id": lecture_id,
            "title": lecture.title,
            "status": lecture.status,
            "slides": formatted_slides,
            "transcription": formatted_segments
        }

    except Exception as e:
        logger.error(f"Error retrieving lecture: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving lecture: {str(e)}"
        )