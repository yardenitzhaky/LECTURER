# app/services/transcription.py
import os
from pathlib import Path
from faster_whisper import WhisperModel
import torch
import moviepy.editor as mp  # Changed import
from typing import List, Dict, Any
import logging
from uuid import uuid4


logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        # Initialize faster-whisper model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        # Initialize the model (using medium for balance of speed and accuracy)
        self.model = WhisperModel("medium", device=device, compute_type=compute_type)
        logger.info(f"Using device: {device}")

    async def extract_audio(self, video_path: str) -> str:
        """Extract audio from video file."""
        try:
            # Create output path
            audio_path = video_path.rsplit('.', 1)[0] + '.wav'
            
            # Extract audio using moviepy
            video = mp.VideoFileClip(video_path)  # Use mp.VideoFileClip
            video.audio.write_audiofile(audio_path)
            video.close()
            
            return audio_path
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file and return detailed transcription with segment-level timing.
        """
        try:
            # Transcribe without word timestamps
            segments, info = self.model.transcribe(
                audio_path,
                word_timestamps=False  # Changed to False since we don't need word timestamps
            )
            
            # Process segments
            processed_segments = []
            full_text = []
            
            for segment in segments:
                processed_segments.append({
                    "id": str(len(processed_segments) + 1), 
                    "start_time": segment.start,
                    "end_time": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob  # Use segment-level confidence
                })
                full_text.append(segment.text)
            
            logger.info(f"Processed {len(processed_segments)} segments")
            return {
                "segments": processed_segments,
                "language": info.language,
                "text": " ".join(full_text)
            }
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise

    async def cleanup(self, audio_path: str):
        """Clean up temporary audio file."""
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logger.error(f"Error cleaning up audio file: {str(e)}")
