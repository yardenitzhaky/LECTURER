# app/api/api.py
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
from app import deps
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize service objects for transcription, presentation processing, and slide matching
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
    Process a lecture by accepting a presentation file and either a video file or URL.
    Creates a new lecture record, extracts slides from the presentation,
    and starts background processing of the video.
    
    Returns lecture ID and processing status.
    """
    try:
        # Validate that either a video file or URL was provided
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

        # Handle video input - either save uploaded file or use URL
        if video:
            video_filename = f"{uuid.uuid4()}_{video.filename}"
            video_path = upload_dir / video_filename
            async with aiofiles.open(video_path, 'wb') as out_file:
                content = await video.read()
                await out_file.write(content)
        else:
            # Handle video URL case
            video_path = video_url

        # Create lecture record in 'processing' state
        lecture = Lecture(
            title=presentation.filename,
            status="processing",
            video_path=str(video_path) if isinstance(video_path, Path) else video_path
        )
        db.add(lecture)
        db.flush()

        # Process presentation immediately to extract slides
        slide_images = await presentation_service.process_presentation(
            presentation_content,
            file_extension
        )

        # Save extracted slides to database with base64-encoded image data
        for index, image_data in enumerate(slide_images):
            slide = Slide(
                lecture_id=lecture.id,
                index=index,
                image_data=image_data
            )
            db.add(slide)

        # Process video in background to avoid blocking the response
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

async def process_video_background(
    video_path: str,
    lecture_id: int,
    db: Session
):
    """
    Background task that processes a video for a lecture.
    
    Steps:
    1. Extract audio from video or download from URL
    2. Transcribe audio to text
    3. Match transcription segments to slides
    4. Update lecture with transcription data
    5. Clean up temporary files
    
    Updates lecture status throughout the process.
    """
    try:
        # Update status to 'downloading'
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "downloading"
        db.commit()
        
        # Extract audio depending on source (local file or URL)
        if not video_path.startswith('http'):
            logger.info(f"Processing local video file: {video_path}")
            audio_path = await transcription_service.extract_audio(video_path)
        else:
            # Handle YouTube/URL case
            logger.info(f"Processing video from URL: {video_path}")
            audio_path = await transcription_service.download_and_extract_audio(video_path)

        logger.info(f"Audio extraction completed. Audio path: {audio_path}")

        # Verify audio file was created successfully
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Update status to 'transcribing' and start transcription
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "transcribing"
        db.commit()
            
        logger.info("Starting transcription...")
        transcription = await transcription_service.transcribe(audio_path)
        logger.info("Transcription completed")

        # Update status to 'matching' and begin slide matching
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "matching"
        db.commit()

        # Get slides for the lecture to match with transcription
        slides = db.query(Slide).filter(Slide.lecture_id == lecture_id).order_by(Slide.index).all()
        
        # Format slides for matching algorithm
        slides_data = [
            {
                'image_data': slide.image_data,
                'index': slide.index
            }
            for slide in slides
        ]

        # Format transcription segments for matching algorithm
        transcription_data = [
            {
                'start_time': segment['start_time'],
                'end_time': segment['end_time'],
                'text': segment['text'],
                'confidence': segment['confidence']
            }
            for segment in transcription['segments']
        ]

        # Match transcription segments to slides
        matched_segments = await slide_matching_service.match_transcription_to_slides(
            video_path,
            slides_data,
            transcription_data
        )

        # Update lecture status to 'completed'
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        lecture.status = "completed"
        
        # Add transcription segments with slide indices to database
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

        # Clean up temporary files
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
    Retrieve complete lecture data including slides and transcription segments.
    
    Returns:
        - Lecture metadata (id, title, status)
        - Slides with base64 image data
        - Transcription segments with timing and slide mapping
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

        # Format slides for API response
        formatted_slides = [
            {
                "imageUrl": slide.image_data,  # Base64-encoded image data
                "index": slide.index
            }
            for slide in slides
        ]

        # Format transcription segments for API response
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

        # Combine all data into a structured response
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