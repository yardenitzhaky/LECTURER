# app/api/summarization.py
import logging
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.utils.common import get_db
from app.db.models import Lecture, Slide, TranscriptionSegment, User
from app.auth import current_active_user
from app.services.summarization import SummarizationService
from app.utils.ocr import extract_text_from_base64_image
from app.schemas import SummarizeRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
summarization_service = SummarizationService()


@router.post("/lectures/{lecture_id}/slides/{slide_index}/summarize")
async def summarize_slide_endpoint(
    lecture_id: int,
    slide_index: int,
    request: SummarizeRequest = SummarizeRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Optional[str]]:
    """Generates and saves a summary for a specific slide."""
    logger.info(f"Summarize request for L:{lecture_id} S:{slide_index}")

    # Verify user owns the lecture first
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.user_id == str(current_user.id)).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    slide = db.query(Slide).filter(Slide.lecture_id == lecture_id, Slide.index == slide_index).with_for_update().first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    lecture_status = lecture.status
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

    # Extract slide content using OCR
    slide_content = ""
    try:
        if slide.image_data:
            slide_content = extract_text_from_base64_image(slide.image_data)
            logger.info(f"Extracted {len(slide_content)} characters from slide {slide_index} using OCR")
    except Exception as ocr_error:
        logger.warning(f"OCR failed for slide {slide_index}: {ocr_error}")
        slide_content = ""

    if not summarization_service.llm:
        logger.error("Summarization service unavailable (likely no API key)")
        raise HTTPException(status_code=503, detail="Summarization service is not configured.")

    try:
        if request.custom_prompt:
            logger.info(f"Using custom prompt for L:{lecture_id} S:{slide_index}: {request.custom_prompt[:50]}...")
            new_summary = await summarization_service.summarize_with_custom_prompt(full_slide_text, request.custom_prompt, slide_content)
        else:
            new_summary = await summarization_service.summarize_text(full_slide_text, slide_content)
        
        if new_summary is None:
            logger.error(f"Summarization returned None for L:{lecture_id} S:{slide_index}")
            raise HTTPException(status_code=503, detail="Summarization service returned no content.")

        slide.summary = new_summary
        db.add(slide)
        db.commit()
        logger.info(f"Summary saved for L:{lecture_id} S:{slide_index}")
        return {"summary": new_summary}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to summarize or save summary for L:{lecture_id} S:{slide_index}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during summarization process: {str(e)}")