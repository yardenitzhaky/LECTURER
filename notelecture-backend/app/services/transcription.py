# app/services/transcription.py
import os
import time
import requests
from pathlib import Path
import moviepy.editor as mp
from typing import List, Dict, Any
import logging
from uuid import uuid4
import yt_dlp


logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        # IVRIT.AI API configuration from settings
        from app.core.config import settings
        self.api_key = settings.ivrit_ai_api_key
        self.base_url = "https://hebrew-ai.com/api/transcribe"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        # How often to poll for status (in seconds)
        self.polling_interval = 12
        # Maximum polling attempts (adjust as needed)
        self.max_polling_attempts = 105 

    async def extract_audio(self, video_path: str) -> str:
        """Extracts audio from a local video file into MP3 format."""
        # Output MP3 instead of WAV
        output_audio_path = Path(video_path).with_suffix('.mp3')
        try:
            logger.info(f"Extracting audio from '{video_path}' to '{output_audio_path}'")
            with mp.VideoFileClip(video_path) as video:
                # Specify codec for MP3
                video.audio.write_audiofile(str(output_audio_path), codec='libmp3lame', logger=None)
            logger.info("Audio extraction successful (MP3).")
            return str(output_audio_path)
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
        Transcribe audio file using IVRIT.AI API and return detailed transcription.
        """
        try:
            # Check if the file exists and is readable
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found at path: {audio_path}")
            
            if not os.access(audio_path, os.R_OK):
                raise PermissionError(f"No permission to read audio file at: {audio_path}")
                
            # Check file format and convert if necessary
            base, ext = os.path.splitext(audio_path)
            if ext.lower() not in ['.mp3', '.wav', '.m4a', '.aac', '.flac']:
                logger.warning(f"File format {ext} may not be supported. Converting to MP3.")
                try:
                    mp3_path = f"{base}.mp3"
                    audio = mp.AudioFileClip(audio_path)
                    audio.write_audiofile(mp3_path)
                    audio_path = mp3_path
                    logger.info(f"Converted audio to MP3: {mp3_path}")
                except Exception as conv_err:
                    logger.error(f"Failed to convert audio: {str(conv_err)}")
                    # Continue with original file if conversion fails
            
            # Step 1: Upload file to IVRIT.AI API
            transcription_id = await self._upload_file(audio_path)
            logger.info(f"File uploaded successfully. Transcription ID: {transcription_id}")
            
            # Step 2: Poll for transcription status
            transcription_result = await self._poll_transcription_status(transcription_id)
            
            # Step 3: Process the result into our expected format
            if transcription_result.get("success") and transcription_result.get("status") == "COMPLETED":
                # Extract the full text and duration
                full_text = transcription_result.get("text", "")
                duration = transcription_result.get("duration", 0)
                
                logger.info(f"Transcription completed successfully. Text length: {len(full_text)}, Duration: {duration}s")
                
                # Break the text into segments if it's very long
                # This simulates the segmentation that Whisper would provide
                # Each segment will be approximately 30 seconds (as a rough estimate)
                if duration > 60:  # Only segment if longer than 1 minute
                    segment_duration = 15 # 30 seconds per segment
                    num_segments = max(1, int(duration / segment_duration))
                    
                    # Roughly divide the text into segments
                    words = full_text.split()
                    words_per_segment = max(1, len(words) // num_segments)
                    
                    processed_segments = []
                    for i in range(num_segments):
                        start_idx = i * words_per_segment
                        end_idx = min(len(words), (i + 1) * words_per_segment)
                        
                        if start_idx >= len(words):
                            break
                            
                        segment_text = " ".join(words[start_idx:end_idx])
                        start_time = i * segment_duration
                        end_time = min(duration, (i + 1) * segment_duration)
                        
                        processed_segments.append({
                            "id": str(i + 1),
                            "start_time": start_time,
                            "end_time": end_time,
                            "text": segment_text,
                            "confidence": 1.0  # Default confidence value
                        })
                else:
                    # For shorter audio, just create one segment
                    processed_segments = [{
                        "id": "1",
                        "start_time": 0,
                        "end_time": duration,
                        "text": full_text,
                        "confidence": 1.0
                    }]
                
                return {
                    "segments": processed_segments,
                    "language": "he",  # Assuming Hebrew for IVRIT.AI
                    "text": full_text
                }
            else:
                error_msg = transcription_result.get('error', 'Unknown error')
                logger.error(f"Transcription failed: {error_msg}")
                raise Exception(f"Transcription failed: {error_msg}")
            
        except FileNotFoundError as fnf:
            logger.error(f"File not found: {str(fnf)}")
            raise
        except PermissionError as pe:
            logger.error(f"Permission error: {str(pe)}")
            raise
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise

    async def _upload_file(self, audio_path: str) -> str:
        """Upload file to IVRIT.AI API and return transcription ID."""
        try:
            # Log the file path and size for debugging
            file_size = os.path.getsize(audio_path)
            logger.info(f"Uploading file: {audio_path} (Size: {file_size} bytes)")
            
            # Create a file tuple with filename, file object, and content type
            # Proper naming is important for some APIs
            filename = os.path.basename(audio_path)
            content_type = 'audio/wav' if audio_path.lower().endswith('.wav') else 'audio/mpeg'
            
            with open(audio_path, "rb") as audio_file:
                # Create file tuple (field name, file object, filename, content type)
                files = {
                    "file": (filename, audio_file, content_type)
                }
                
                # Debug log the request details
                logger.info(f"Making POST request to: {self.base_url}")
                logger.info(f"With headers: {self.headers}")
                
                # Make request with verify=True for secure connections
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    files=files,
                    timeout=60  # Add timeout to prevent hanging requests
                )
                
                # Debug log the response
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response content: {response.text[:500]}...")  # Truncate long responses
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("success"):
                            return data.get("transcription_id")
                        else:
                            error_msg = data.get("error", "Unknown error")
                            logger.error(f"API error: {error_msg}")
                            raise Exception(f"API error: {error_msg}")
                    except ValueError as json_err:
                        logger.error(f"Failed to parse JSON response: {str(json_err)}")
                        raise Exception(f"Invalid JSON response from API: {response.text}")
                else:
                    # Try to parse error response as JSON if possible
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("error", "No detail provided")
                        logger.error(f"HTTP error {response.status_code}: {error_detail}")
                        raise Exception(f"HTTP error {response.status_code}: {error_detail}")
                    except ValueError:
                        logger.error(f"HTTP error: {response.status_code} - {response.text}")
                        raise Exception(f"HTTP error: {response.status_code} - {response.text}")
                    
        except requests.RequestException as req_err:
            # Handle network-related errors separately
            logger.error(f"Request error: {str(req_err)}")
            raise Exception(f"Network error communicating with IVRIT.AI API: {str(req_err)}")
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise

    async def _poll_transcription_status(self, transcription_id: str) -> Dict[str, Any]:
        """Poll for transcription status until completion or failure."""
        attempts = 0
        
        while attempts < self.max_polling_attempts:
            try:
                url = f"{self.base_url}?id={transcription_id}"
                logger.info(f"Polling transcription status: {url}")
                
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        status = data.get("status")
                        
                        logger.info(f"Transcription status: {status} (attempt {attempts+1}/{self.max_polling_attempts})")
                        
                        # If completed or failed, return the result
                        if status == "COMPLETED" or status == "FAILED":
                            return data
                            
                        # For IN_QUEUE or PENDING or IN_PROGRESS, continue polling
                        if status in ["IN_QUEUE", "PENDING", "IN_PROGRESS"]:
                            pass  # Continue to wait and try again
                        else:
                            logger.warning(f"Unexpected status: {status}")
                    except ValueError as json_err:
                        logger.error(f"Failed to parse JSON response: {str(json_err)}")
                        logger.error(f"Response text: {response.text[:500]}...")
                        
                    # Wait and try again
                    attempts += 1
                    # Use exponential backoff for more efficient polling
                    # Start with polling_interval, then increase gradually
                    wait_time = self.polling_interval * (1.2 ** min(attempts // 5, 5))
                    logger.info(f"Waiting {wait_time:.1f} seconds before next poll")
                    time.sleep(wait_time)
                    
                elif response.status_code == 404:
                    # The transcription job might not exist
                    logger.error(f"Transcription ID not found: {transcription_id}")
                    raise Exception(f"Transcription ID not found: {transcription_id}")
                    
                elif response.status_code == 401 or response.status_code == 403:
                    # Authentication issues
                    logger.error(f"Authentication error (status {response.status_code}): {response.text}")
                    raise Exception(f"Authentication error (status {response.status_code}): {response.text}")
                    
                else:
                    # Other HTTP errors
                    logger.error(f"HTTP error: {response.status_code} - {response.text}")
                    
                    # For temporary server errors (5xx), we can retry
                    if 500 <= response.status_code < 600:
                        logger.info(f"Server error, will retry (attempt {attempts+1}/{self.max_polling_attempts})")
                        attempts += 1
                        time.sleep(self.polling_interval * 2)  # Wait longer for server errors
                    else:
                        raise Exception(f"HTTP error: {response.status_code} - {response.text}")
                    
            except requests.Timeout:
                logger.warning(f"Request timed out, retrying (attempt {attempts+1}/{self.max_polling_attempts})")
                attempts += 1
                time.sleep(self.polling_interval)
                
            except requests.RequestException as req_err:
                logger.error(f"Request error: {str(req_err)}")
                attempts += 1
                if attempts >= 3:  # After 3 network errors, raise exception
                    raise Exception(f"Network error communicating with IVRIT.AI API: {str(req_err)}")
                time.sleep(self.polling_interval * 2)
                
            except Exception as e:
                logger.error(f"Error polling transcription status: {str(e)}")
                raise
                
        # If we reach here, polling timed out
        logger.error(f"Polling timed out after {self.max_polling_attempts} attempts")
        raise Exception(f"Transcription timed out after {self.max_polling_attempts * self.polling_interval} seconds")

    async def cleanup(self, audio_path: str):
        """Clean up temporary audio file."""
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logger.error(f"Error cleaning up audio file: {str(e)}")