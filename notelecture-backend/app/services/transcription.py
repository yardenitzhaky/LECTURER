import os
from pathlib import Path
from faster_whisper import WhisperModel
import torch
import moviepy.editor as mp  # Changed import
from typing import List, Dict, Any
import logging

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
        Transcribe audio file and return detailed transcription with word-level timing.
        """
        try:
            # Transcribe with word-level timestamps
            segments, info = self.model.transcribe(
                audio_path,
                word_timestamps=True
            )
            
            # Process segments and words
            processed_segments = []
            full_text = []
            
            for segment in segments:
                words = []
                segment_confidence = []  # Initialize list to collect word confidences
                for word in segment.words:
                    words.append({
                        "text": word.word.strip(),
                        "start_time": word.start,
                        "end_time": word.end,
                        "confidence": word.probability  # Use word.probability for confidence
                    })
                    segment_confidence.append(word.probability)  # Collect word confidences
                
                # Calculate average confidence for the segment
                avg_segment_confidence = sum(segment_confidence) / len(segment_confidence) if segment_confidence else 0
                
                processed_segments.append({
                    "start_time": segment.start,
                    "end_time": segment.end,
                    "text": segment.text.strip(),
                    "words": words,
                    "confidence": avg_segment_confidence  # Use average confidence for segment
                })
                full_text.append(segment.text)
            
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