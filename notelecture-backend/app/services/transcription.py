# app/services/transcription.py
import os
from pathlib import Path
from faster_whisper import WhisperModel
import torch
import moviepy.editor as mp  # Changed import
from typing import List, Dict, Any
import logging
from uuid import uuid4
import yt_dlp


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

    async def download_and_extract_audio(self, video_url: str) -> str:
        """Download video from URL and extract audio."""
        try:
            # Create uploads directory if it doesn't exist
            os.makedirs("uploads", exist_ok=True)
            
            # Create a unique filename with full path
            filename = str(uuid4())
            output_path = os.path.join("uploads", f"{filename}.mp3")
            temp_path = os.path.join("uploads", f"{filename}.%(ext)s")
            
            logger.info(f"Downloading from URL: {video_url}")
            logger.info(f"Output will be saved to: {output_path}")
            
            # Setup yt-dlp options
            ydl_opts = {
            'format': 'worstaudio/worst',  # Use lowest quality audio to speed up download
            'outtmpl': temp_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',  # Lower quality for faster processing
            }],
            # Add fragment options to speed up downloads
            'socket_timeout': 30,  # Timeout if download takes too long
            'retries': 5,          # Don't retry too many times
            'verbose': False       # Turn off verbose output
            }
        
            
            # Download the video and extract audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Starting download with yt-dlp")
                ydl.download([video_url])
                logger.info("Download completed")
            
            # Verify the file exists
            if not os.path.exists(output_path):
                logger.error(f"Expected output file not found: {output_path}")
                # Try to find what was actually downloaded
                potential_files = [f for f in os.listdir("uploads") if f.startswith(filename)]
                if potential_files:
                    logger.info(f"Found alternative files: {potential_files}")
                    # Use the first matching file
                    output_path = os.path.join("uploads", potential_files[0])
                    logger.info(f"Using alternative file: {output_path}")
                else:
                    raise FileNotFoundError(f"No downloaded file found with prefix {filename}")
            
            logger.info(f"Successfully downloaded and extracted audio to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading video from URL: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file and return detailed transcription with segment-level timing.
        Keep the original language instead of translating to English.
        """
        try:
            # Transcribe without word timestamps and WITHOUT translating to English
            segments, info = self.model.transcribe(
                audio_path,
                word_timestamps=False,  
                beam_size=5,
                task="transcribe",  # Important: Use "transcribe" instead of default "translate"
                language=None,      # Setting language to None allows auto-detection
                translate=False     # Explicitly disable translation
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
            
            logger.info(f"Processed {len(processed_segments)} segments in detected language: {info.language}")
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