# app/services/transcription.py
import os
import time
import httpx
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Any
import logging
from uuid import uuid4
import traceback
from app.core.config import settings

# Check if moviepy is available
try:
    import moviepy.editor as mp
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    mp = None
    logging.warning("moviepy not available - will use external service for audio extraction")

# Check if yt-dlp is available  
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    yt_dlp = None
    logging.warning("yt_dlp not available - will use external service for video download")

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        # RunPod API configuration from settings
        from app.core.config import settings
        self.api_key = settings.runpod_api_key
        self.endpoint_id = settings.runpod_endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}" if self.endpoint_id else None
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        } if self.api_key else {} # Only include header if key exists
        # Use an AsyncClient instance for connection pooling
        # Increased timeout for potentially large file uploads/long polling
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) # 3 minutes total, 10s connect

        # How often to poll for status (in seconds)
        self.polling_interval = 5
        # Maximum polling attempts (adjust as needed) - increased for longer audio
        self.max_polling_attempts = 360 # Increased to ~30 minutes max polling time

    # --- Synchronous Helper for extract_audio ---
    def _sync_extract_audio(self, video_path: str, output_audio_path: str):
        """Synchronous part of audio extraction."""
        try:
            logger.info(f"[Sync] Extracting audio from '{video_path}' to '{output_audio_path}'")
            # Use ffmpeg=settings.FFMPEG_PATH if you added an FFMPEG_PATH setting
            # from app.core.config import settings # Import settings inside if needed
            # config_path = getattr(settings, 'FFMPEG_PATH', None)
            # video = mp.VideoFileClip(video_path, ffmpeg_binary=config_path) if config_path else mp.VideoFileClip(video_path)

            with mp.VideoFileClip(video_path) as video:
                # Added check for audio track
                if video.audio is None:
                     raise ValueError(f"No audio track found in video file: {video_path}")
                video.audio.write_audiofile(output_audio_path, codec='libmp3lame', logger=None)
            logger.info("[Sync] Audio extraction successful (MP3).")
        except Exception as e:
            logger.error(f"[Sync] Error extracting audio: {str(e)}")
            raise # Re-raise to be caught by the async wrapper

    async def extract_audio(self, video_path: str) -> str:
        """Extracts audio from a local video file into MP3 format."""
        # Try external service first if moviepy is not available or external service is configured
        if not MOVIEPY_AVAILABLE or settings.EXTERNAL_SERVICE_URL:
            try:
                return await self._extract_audio_external(video_path)
            except Exception as e:
                logger.warning(f"External audio extraction failed: {e}")
                if not MOVIEPY_AVAILABLE:
                    raise Exception("Audio extraction requires moviepy which is not available - please use external service")
        
        # Fallback to local processing if moviepy is available
        if MOVIEPY_AVAILABLE:
            output_audio_path = str(Path(video_path).with_suffix('.mp3'))
            loop = asyncio.get_running_loop()
            try:
                # Run the blocking moviepy operation in a thread pool executor
                await loop.run_in_executor(None, self._sync_extract_audio, video_path, output_audio_path)
                return output_audio_path
            except Exception as e:
                logger.error(f"Local audio extraction failed: {e}")
                raise
        else:
            raise Exception("Audio extraction requires moviepy which is not available - please use external service")

    async def _extract_audio_external(self, video_path: str) -> str:
        """Extract audio using external service."""
        if not settings.EXTERNAL_SERVICE_URL:
            raise Exception("External service URL not configured")
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Read video file
                with open(video_path, 'rb') as video_file:
                    files = {"video_file": (os.path.basename(video_path), video_file, "video/mp4")}
                    headers = {}
                    if settings.EXTERNAL_SERVICE_API_KEY:
                        headers["Authorization"] = f"Bearer {settings.EXTERNAL_SERVICE_API_KEY}"
                    
                    response = await client.post(
                        f"{settings.EXTERNAL_SERVICE_URL}/extract-audio/",
                        files=files,
                        headers=headers
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if result.get("status") == "success":
                        # For now, return the original video path with .mp3 extension
                        # In production, the external service would return the actual audio file
                        output_audio_path = str(Path(video_path).with_suffix('.mp3'))
                        logger.info(f"External audio extraction successful: {output_audio_path}")
                        return output_audio_path
                    else:
                        raise Exception(f"External service returned: {result.get('message', 'Unknown error')}")
                        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling external audio service: {e}")
            raise Exception(f"External audio extraction failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling external audio service: {e}")
            raise

    # --- Synchronous Helper for download_and_extract_audio ---
    def _sync_download_and_extract(self, video_url: str):
        """Synchronous part of downloading and extracting audio."""
        try:
            # Use /tmp directory for Vercel serverless environment
            upload_dir = "/tmp"
            filename = str(uuid4())
            # yt-dlp determines final filename, provide a path template
            temp_path_template = os.path.join(upload_dir, f"{filename}.%(ext)s")

            logger.info(f"[Sync] Downloading from URL: {video_url}")
            logger.info(f"[Sync] Temporary path template: {temp_path_template}")

            ydl_opts = {
                'format': 'worstaudio/worst', # Get the worst quality audio stream (smallest size, fastest download)
                'outtmpl': temp_path_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '64', # Low quality audio, sufficient for transcription
                }],
                'socket_timeout': 30,
                'retries': 5,
                'verbose': False,
                'quiet': True, # Suppress yt-dlp console output
                'noprogress': True, # Don't show progress bars
                'ffmpeg_location': os.getenv("FFMPEG_PATH"), # Optional: if ffmpeg not in PATH
                'no_warnings': True,
                'logtostderr': False, # Don't log to stderr
            }

            output_path = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("[Sync] Starting download and extraction with yt-dlp")
                info_dict = ydl.extract_info(video_url, download=True)
                # yt-dlp returns info_dict after processing, including the final filepath
                # Find the final path of the audio file
                # The exact key can vary, check info_dict structure or rely on outtmpl postprocessing
                # A common pattern is the postprocessed file being next to the original temp file
                # Or checking the files created in the upload directory
                logger.info("[Sync] Download completed, checking for output file.")
                expected_output_prefix = os.path.join(upload_dir, filename)
                # Search for files starting with the filename and ending with .mp3
                potential_files = [f for f in os.listdir(upload_dir) if f.startswith(filename) and f.endswith('.mp3')]

                if potential_files:
                    # Assume the first found MP3 file is the correct one
                    output_path = os.path.join(upload_dir, potential_files[0])
                    logger.info(f"[Sync] Found extracted MP3 file: {output_path}")
                else:
                     # This might happen if extraction failed but download succeeded
                    all_temp_files = [f for f in os.listdir(upload_dir) if f.startswith(filename)]
                    logger.warning(f"[Sync] Expected MP3 output not found. Found temporary files: {all_temp_files}")
                    if all_temp_files:
                         # Clean up temp files if MP3 wasn't created
                         for temp_file in all_temp_files:
                              try: os.remove(os.path.join(upload_dir, temp_file))
                              except Exception as cleanup_err: logger.warning(f"[Sync] Failed to cleanup temp file {temp_file}: {cleanup_err}")
                         raise FileNotFoundError(f"MP3 extraction failed for URL: {video_url}")
                    else:
                         # No files at all means download likely failed
                         raise FileNotFoundError(f"Download or extraction failed for URL: {video_url}. No temporary files found.")


            if not output_path or not os.path.exists(output_path):
                raise FileNotFoundError(f"yt-dlp did not produce the expected MP3 file at {output_path}")

            logger.info(f"[Sync] Successfully downloaded and extracted audio to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Sync] Error downloading video from URL: {str(e)}")
            logger.error(traceback.format_exc())
            # Clean up temp files if possible
            if 'filename' in locals() and 'upload_dir' in locals():
                 temp_files = [f for f in os.listdir(upload_dir) if f.startswith(filename)]
                 for temp_file in temp_files:
                     try: os.remove(os.path.join(upload_dir, temp_file))
                     except Exception: pass
                 logger.info(f"[Sync] Cleaned up temporary files for {filename}")

            raise

    async def download_and_extract_audio(self, video_url: str) -> str:
        """Download video from URL and extract audio."""
        # Try external service first if yt-dlp/moviepy are not available or external service is configured
        if not (YT_DLP_AVAILABLE and MOVIEPY_AVAILABLE) or settings.EXTERNAL_SERVICE_URL:
            try:
                return await self._download_and_extract_external(video_url)
            except Exception as e:
                logger.warning(f"External video download failed: {e}")
                if not (YT_DLP_AVAILABLE and MOVIEPY_AVAILABLE):
                    raise Exception("Video download requires yt_dlp which is not available - please use external service")
        
        # Fallback to local processing if dependencies are available
        if YT_DLP_AVAILABLE and MOVIEPY_AVAILABLE:
            loop = asyncio.get_running_loop()
            try:
                # Run the blocking yt-dlp operation in a thread pool executor
                output_path = await loop.run_in_executor(None, self._sync_download_and_extract, video_url)
                return output_path
            except Exception as e:
                logger.error(f"Local video download failed: {e}")
                raise
        else:
            raise Exception("Video download requires yt_dlp which is not available - please use external service")

    async def _download_and_extract_external(self, video_url: str) -> str:
        """Download video and extract audio using external service."""
        if not settings.EXTERNAL_SERVICE_URL:
            raise Exception("External service URL not configured")
        
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:  # Longer timeout for video download
                data = {"video_url": video_url}
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                if settings.EXTERNAL_SERVICE_API_KEY:
                    headers["Authorization"] = f"Bearer {settings.EXTERNAL_SERVICE_API_KEY}"
                
                response = await client.post(
                    f"{settings.EXTERNAL_SERVICE_URL}/download-extract-audio/",
                    data=data,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("status") == "success":
                    # Generate a temporary file path for the audio
                    upload_dir = "/tmp"
                    filename = str(uuid4())
                    output_path = os.path.join(upload_dir, f"{filename}.mp3")
                    
                    logger.info(f"External video download and extraction successful: {output_path}")
                    return output_path
                else:
                    raise Exception(f"External service returned: {result.get('message', 'Unknown error')}")
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling external video service: {e}")
            raise Exception(f"External video download failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling external video service: {e}")
            raise

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using RunPod API and return detailed transcription.
        (Uses async HTTP calls and sleeps).
        """
        # --- ADD API KEY CHECK ---
        if not self.api_key or self.api_key == "YOUR_RUNPOD_API_KEY":
             logger.error("RunPod API Key is not configured or is placeholder.")
             raise Exception("Transcription service API key is not configured.")
        if not self.endpoint_id:
             logger.error("RunPod endpoint ID is not configured.")
             raise Exception("RunPod endpoint ID is not configured.")
        if not self.base_url:
             logger.error("RunPod base URL could not be constructed.")
             raise Exception("RunPod endpoint configuration is incomplete.")
        if not self.headers: # Ensure headers are set if key was just loaded or became valid
             self.headers = {
                 "Content-Type": "application/json",
                 "Authorization": f"Bearer {self.api_key}"
             }
        # --- END API KEY CHECK ---


        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found at path: {audio_path}")
            if not os.access(audio_path, os.R_OK):
                raise PermissionError(f"No permission to read audio file at: {audio_path}")

            # Step 1: Submit job to RunPod API (async)
            job_id = await self._submit_runpod_job(audio_path)
            logger.info(f"Job submitted successfully. RunPod Job ID: {job_id}")

            # Step 2: Poll for job status (async)
            transcription_result = await self._poll_runpod_job_status(job_id)

            # Step 3: Process the result
            if transcription_result.get("success") and transcription_result.get("status") == "COMPLETED":
                full_text = transcription_result.get("text", "")
                duration = transcription_result.get("duration", 0)
                language_used = transcription_result.get("language", "unknown")
                logger.info(f"Transcription completed (Lang: {language_used}). Text length: {len(full_text)}, Duration: {duration}s")

                # *** Important: Re-evaluate Segmentation ***
                # Check if the RunPod response contains actual segments with timestamps.
                # If it does, group them into 10-15 second chunks for better slide matching.
                api_segments = transcription_result.get("segments") # Check if 'segments' key exists
                if api_segments and isinstance(api_segments, list) and len(api_segments) > 0 and 'start' in api_segments[0]:
                     logger.info(f"Received {len(api_segments)} segments directly from API. Grouping into 10-15 second chunks.")
                     
                     # Group segments into 10-15 second chunks
                     chunk_duration = 12.0  # Target 12 seconds per chunk
                     processed_segments = []
                     current_chunk_text = []
                     current_chunk_start = None
                     current_chunk_end = None
                     chunk_id = 1
                     
                     for seg in api_segments:
                         if seg.get('start') is None:
                             continue
                             
                         seg_start = float(seg.get("start", 0))
                         seg_end = float(seg.get("end", seg_start + 1))
                         seg_text = seg.get("text", "").strip()
                         
                         if not seg_text:
                             continue
                         
                         # Initialize first chunk
                         if current_chunk_start is None:
                             current_chunk_start = seg_start
                             current_chunk_end = seg_end
                             current_chunk_text.append(seg_text)
                         # Check if adding this segment would exceed chunk duration
                         elif (seg_end - current_chunk_start) <= chunk_duration:
                             # Add to current chunk
                             current_chunk_text.append(seg_text)
                             current_chunk_end = seg_end
                         else:
                             # Save current chunk and start new one
                             if current_chunk_text:
                                 processed_segments.append({
                                     "id": str(chunk_id),
                                     "start_time": current_chunk_start,
                                     "end_time": current_chunk_end,
                                     "text": " ".join(current_chunk_text),
                                     "confidence": 0.9  # High confidence for API segments
                                 })
                                 chunk_id += 1
                             
                             # Start new chunk with current segment
                             current_chunk_start = seg_start
                             current_chunk_end = seg_end
                             current_chunk_text = [seg_text]
                     
                     # Don't forget the last chunk
                     if current_chunk_text:
                         processed_segments.append({
                             "id": str(chunk_id),
                             "start_time": current_chunk_start,
                             "end_time": current_chunk_end,
                             "text": " ".join(current_chunk_text),
                             "confidence": 0.9
                         })
                     
                     logger.info(f"Grouped {len(api_segments)} API segments into {len(processed_segments)} chunks of ~{chunk_duration}s each.")
                else:
                     logger.warning("API did not provide detailed segments with timestamps. Approximating segmentation based on duration.")
                     # Keep the approximate segmentation logic as a fallback
                     segment_duration = 15 # seconds per segment for approximation
                     num_segments = max(1, int(duration / segment_duration)) if duration > 0 else 1
                     # Fallback: If duration is 0 but text exists, create one segment
                     if duration == 0 and full_text.strip():
                          num_segments = 1
                          duration = 5 # Assign a small arbitrary duration
                          segment_duration = 5


                     words = full_text.split()
                     words_per_segment = max(1, len(words) // num_segments) if num_segments > 0 else len(words)
                     processed_segments = []
                     for i in range(num_segments):
                         start_idx = i * words_per_segment
                         end_idx = min(len(words), (i + 1) * words_per_segment)
                         if start_idx >= len(words) and i > 0: break # Avoid creating empty segments if last segment is tiny
                         segment_text = " ".join(words[start_idx:end_idx])
                         start_time = float(i * segment_duration)
                         end_time = float(min(duration, (i + 1) * segment_duration)) if duration > 0 else float(segment_duration)
                         processed_segments.append({
                             "id": str(i + 1), "start_time": start_time, "end_time": end_time,
                             "text": segment_text, "confidence": 0.8 # Indicate lower confidence for approximation
                         })
                     # Ensure at least one segment if there was any text
                     if not processed_segments and full_text.strip():
                          processed_segments.append({
                              "id": "1", "start_time": 0.0, "end_time": float(duration if duration > 0 else 5.0),
                              "text": full_text.strip(), "confidence": 0.8
                          })


                return {
                    "segments": processed_segments,
                    "language": language_used,
                    "text": full_text # Still return full text if needed elsewhere
                }
            else:
                error_msg = transcription_result.get('error', 'Unknown error from API')
                status = transcription_result.get('status', 'N/A')
                logger.error(f"Transcription failed (Status: {status}): {error_msg}")
                raise Exception(f"Transcription failed (Status: {status}): {error_msg}")

        except FileNotFoundError as fnf:
            logger.error(f"File not found: {str(fnf)}")
            raise
        except PermissionError as pe:
            logger.error(f"Permission error: {str(pe)}")
            raise
        except Exception as e:
            logger.error(f"Error during transcription process: {str(e)}", exc_info=True)
            raise

    async def _submit_runpod_job(self, audio_path: str) -> str:
        """Submit transcription job to RunPod API and return job ID."""
        # Ensure headers include the API key
        if not self.headers:
             logger.error("Attempted to submit job without API key headers.")
             raise Exception("Transcription API key is missing.")

        try:
            # Read audio file and encode to base64
            file_size = os.path.getsize(audio_path)
            logger.info(f"Preparing RunPod job for file: {audio_path} (Size: {file_size} bytes)")
            
            import base64
            async with aiofiles.open(audio_path, "rb") as audio_file:
                audio_content = await audio_file.read()
                audio_base64 = base64.b64encode(audio_content).decode('utf-8')

            # Prepare RunPod job payload for IVRIT.AI template
            job_payload = {
                'input': {
                    'transcribe_args': {
                        'blob': audio_base64,  # Use 'blob' for base64 audio data
                        'language': 'he'  # Hebrew language code (lowercase)
                    }
                }
            }

            url = f"{self.base_url}/run"
            logger.info(f"Making async POST request to RunPod: {url}")

            # Use the shared client instance
            response = await self.http_client.post(
                url,
                headers=self.headers,
                json=job_payload
            )

            logger.info(f"Response status code: {response.status_code}")
            response_text = response.text
            logger.info(f"Response content preview: {response_text[:500]}...") # Log more of response for debugging

            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx

            data = response.json()
            job_id = data.get("id")
            if not job_id:
                error_msg = data.get('error', 'Unknown error from RunPod API')
                logger.error(f"RunPod API did not return job ID: {error_msg}")
                raise Exception(f"RunPod API error: {error_msg}")
            
            logger.info(f"RunPod job submitted successfully with ID: {job_id}")
            return job_id

        except httpx.HTTPStatusError as http_err:
             error_detail = f"HTTP error during RunPod job submission: {http_err.response.status_code}"
             try:
                  # Try to parse error body for more detail
                  err_data = http_err.response.json()
                  if 'error' in err_data:
                       error_detail += f" - Detail: {err_data['error']}"
                  elif 'detail' in err_data:
                       error_detail += f" - Detail: {err_data['detail']}"
             except Exception:
                  error_detail += f" - Body: {http_err.response.text[:200]}..." # Log raw body if JSON parse fails

             logger.error(error_detail)
             # Raise specific exceptions based on status code
             if http_err.response.status_code == 401 or http_err.response.status_code == 403:
                  raise Exception("Authentication failed with RunPod API. Check API key.") from http_err
             elif http_err.response.status_code == 400:
                  raise Exception(f"Bad request sent to RunPod API: {error_detail}") from http_err
             else:
                 raise Exception(f"HTTP error during RunPod job submission: {http_err.response.status_code}") from http_err

        except httpx.RequestError as req_err: # Includes timeouts, connection errors
            logger.error(f"Network error during RunPod job submission: {str(req_err)}")
            raise Exception(f"Network error communicating with RunPod API: {str(req_err)}") from req_err
        except Exception as e:
            # Catch any other unexpected errors during the job submission
            logger.error(f"Unexpected error during RunPod job submission: {str(e)}", exc_info=True)
            raise

    async def _poll_runpod_job_status(self, job_id: str) -> Dict[str, Any]:
        """Poll for RunPod job status using httpx until completion or failure."""
         # Ensure headers include the API key
        if not self.headers:
             logger.error("Attempted to poll status without API key headers.")
             raise Exception("RunPod API key is missing.")

        attempts = 0
        url = f"{self.base_url}/status/{job_id}"

        while attempts < self.max_polling_attempts:
            try:
                logger.info(f"Polling RunPod job status: {url} (Attempt {attempts + 1}/{self.max_polling_attempts})")

                # Use the shared client instance
                response = await self.http_client.get(url, headers=self.headers, timeout=45.0)
                response.raise_for_status() # Check for HTTP errors

                data = response.json()
                status = data.get("status")
                logger.info(f"RunPod Job ID {job_id} status: {status}")

                if status == "COMPLETED":
                    # Extract the output from RunPod response
                    output = data.get("output", [])
                    
                    # Handle RunPod IVRIT.AI format: output is a list with nested 'result' containing JSON strings
                    segments = []
                    if isinstance(output, list) and len(output) > 0:
                        # Extract segments from the nested result structure
                        for item in output:
                            if isinstance(item, dict) and 'result' in item:
                                result_list = item['result']
                                if isinstance(result_list, list):
                                    # Parse each JSON string in the result list
                                    import json
                                    for json_str in result_list:
                                        try:
                                            segment_data = json.loads(json_str)
                                            # Extract the relevant fields
                                            segments.append({
                                                'text': segment_data.get('text', ''),
                                                'start': segment_data.get('start', 0),
                                                'end': segment_data.get('end', 0)
                                            })
                                        except (json.JSONDecodeError, KeyError) as e:
                                            logger.warning(f"Failed to parse segment JSON: {e}")
                                            continue
                    
                    # Combine all text from segments
                    full_text = " ".join([seg.get("text", "") for seg in segments if seg.get("text")])
                    # Calculate total duration from segments
                    total_duration = max([seg.get("end", 0) for seg in segments], default=0)
                    
                    logger.info(f"Parsed {len(segments)} segments from RunPod response")
                    logger.info(f"Full text length: {len(full_text)}, Duration: {total_duration}s")
                    
                    return {
                        "success": True,
                        "status": "COMPLETED",
                        "text": full_text,
                        "duration": total_duration,
                        "language": "he",  # Hebrew
                        "segments": segments
                    }
                elif status == "FAILED":
                    error_msg = data.get("error", "RunPod job failed")
                    logger.error(f"RunPod job {job_id} failed: {error_msg}")
                    return {
                        "success": False,
                        "status": "FAILED",
                        "error": error_msg
                    }
                elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                    attempts += 1
                    # Exponential backoff for polling interval
                    wait_time = self.polling_interval * (1.2 ** min(attempts // 3, 5)) # Faster initial polling, then slow down
                    logger.info(f"Waiting {wait_time:.1f} seconds before next poll for Job ID {job_id}...")
                    await asyncio.sleep(wait_time) # Use async sleep
                else:
                    logger.warning(f"Unexpected status received for Job ID {job_id}: {status}. Treating as temporary issue and retrying.")
                    attempts += 1
                    await asyncio.sleep(self.polling_interval * 2) # Wait longer for unexpected status

            except httpx.HTTPStatusError as http_err:
                error_detail = f"HTTP error during polling status for Job ID {job_id}: {http_err.response.status_code}"
                try:
                    err_data = http_err.response.json()
                    if 'error' in err_data:
                        error_detail += f" - Detail: {err_data['error']}"
                    elif 'detail' in err_data:
                       error_detail += f" - Detail: {err_data['detail']}"
                except Exception:
                     error_detail += f" - Body: {http_err.response.text[:200]}..."

                logger.error(error_detail)

                # Handle specific HTTP errors
                if http_err.response.status_code == 404:
                     raise Exception(f"Polling failed: RunPod Job ID not found: {job_id}") from http_err
                elif http_err.response.status_code in [401, 403]:
                     raise Exception(f"Polling failed: Authentication error polling status (status {http_err.response.status_code})") from http_err
                elif 500 <= http_err.response.status_code < 600:
                     logger.warning(f"Server error ({http_err.response.status_code}) during polling for Job ID {job_id}, retrying...")
                     attempts += 1
                     await asyncio.sleep(self.polling_interval * 2.5) # Wait longer for server errors
                else: # Other client errors (4xx) are likely permanent
                     raise Exception(f"Polling failed: HTTP error polling status: {http_err.response.status_code}") from http_err

            except httpx.RequestError as req_err: # Includes timeouts, connection errors
                logger.warning(f"Network error during polling for Job ID {job_id}: {str(req_err)}. Retrying...")
                attempts += 1
                await asyncio.sleep(self.polling_interval * 1.5)

            except Exception as e:
                 logger.error(f"Unexpected error polling RunPod job status for Job ID {job_id}: {str(e)}", exc_info=True)
                 # Depending on the error, you might want to retry or fail immediately
                 # For now, let's retry after a delay
                 attempts += 1
                 await asyncio.sleep(self.polling_interval * 2)


        logger.error(f"Polling timed out after {self.max_polling_attempts} attempts for Job ID {job_id}")
        raise Exception(f"RunPod job timed out after ~{int(self.max_polling_attempts * self.polling_interval / 60)} minutes.")

    async def cleanup(self, *paths_to_delete: str):
        """Clean up temporary files asynchronously."""
        loop = asyncio.get_running_loop()
        tasks = []
        for audio_path in paths_to_delete:
            if audio_path and os.path.exists(audio_path):
                logger.info(f"Scheduled cleanup for: {audio_path}")
                # Use aiofiles.os.remove if needed for large scale, but os.remove is usually fine for single files
                tasks.append(loop.run_in_executor(None, os.remove, audio_path))
            elif audio_path:
                logger.warning(f"Cleanup requested for non-existent path: {audio_path}")

        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"Cleanup tasks completed.")
            except Exception as e:
                 # Exceptions from run_in_executor are usually caught by gather with return_exceptions=True
                 # We can inspect the results if needed, but a general error log is sufficient for cleanup
                 logger.error(f"Error during cleanup tasks: {e}")

    async def close_client(self):
        """Closes the httpx client. Call this during application shutdown."""
        if self.http_client:
             await self.http_client.aclose()
             logger.info("HTTPX client closed.")

# Note: The background task should handle cleanup, including potential temporary video files
# and the generated audio file. The `process_video_background` function in app/api/api.py
# already calls `transcription_service.cleanup(audio_path)`. It should also clean up
# the temporary video file if one was saved locally from an upload.
# Checking app/api/api.py line 180 confirms `video_file_to_delete` is handled.