# app/services/transcription.py
import os
import time
import httpx # Add httpx import
import asyncio # Add asyncio import
import aiofiles # Add aiofiles import
from pathlib import Path
import moviepy.editor as mp
from typing import List, Dict, Any
import logging
from uuid import uuid4
import yt_dlp
import traceback # Keep traceback for error logging

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        # IVRIT.AI API configuration from settings
        from app.core.config import settings
        self.api_key = settings.ivrit_ai_api_key
        self.base_url = "https://hebrew-ai.com/api/transcribe"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        } if self.api_key else {} # Only include header if key exists
        # Use an AsyncClient instance for connection pooling
        # Increased timeout for potentially large file uploads/long polling
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) # 3 minutes total, 10s connect

        # How often to poll for status (in seconds)
        self.polling_interval = 12
        # Maximum polling attempts (adjust as needed) - increased for longer audio
        self.max_polling_attempts = 300 # Increased to ~1 hour max polling time

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
        """Extracts audio from a local video file into MP3 format (using executor)."""
        output_audio_path = str(Path(video_path).with_suffix('.mp3'))
        loop = asyncio.get_running_loop()
        try:
            # Run the blocking moviepy operation in a thread pool executor
            await loop.run_in_executor(None, self._sync_extract_audio, video_path, output_audio_path)
            return output_audio_path
        except Exception as e:
            logger.error(f"Async wrapper caught error during audio extraction: {e}")
            raise

    # --- Synchronous Helper for download_and_extract_audio ---
    def _sync_download_and_extract(self, video_url: str):
        """Synchronous part of downloading and extracting audio."""
        try:
            # Use settings.UPLOADS_DIR consistently
            from app.core.config import settings # Import settings here if needed by sync function
            upload_dir = settings.UPLOADS_DIR
            os.makedirs(upload_dir, exist_ok=True)
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
        """Download video from URL and extract audio (using executor)."""
        loop = asyncio.get_running_loop()
        try:
            # Run the blocking yt-dlp operation in a thread pool executor
            output_path = await loop.run_in_executor(None, self._sync_download_and_extract, video_url)
            return output_path
        except Exception as e:
            logger.error(f"Async wrapper caught error during download/extraction: {e}")
            raise

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using IVRIT.AI API and return detailed transcription.
        (Uses async HTTP calls and sleeps).
        """
        # --- ADD API KEY CHECK ---
        if not self.api_key or self.api_key == "YOUR_IVRIT_AI_API_KEY":
             logger.error("IVRIT.AI API Key is not configured or is placeholder.")
             raise Exception("Transcription service API key is not configured.")
        if not self.headers: # Ensure headers are set if key was just loaded or became valid
             self.headers = {"Authorization": f"Bearer {self.api_key}"}
        # --- END API KEY CHECK ---


        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found at path: {audio_path}")
            if not os.access(audio_path, os.R_OK):
                raise PermissionError(f"No permission to read audio file at: {audio_path}")

            # File format check/conversion (keep sync for now, usually fast unless huge file)
            # Consider checking file size here and raising a helpful error if too large for API?

            # Step 1: Upload file to IVRIT.AI API (async)
            transcription_id = await self._upload_file(audio_path)
            logger.info(f"File uploaded successfully. Transcription ID: {transcription_id}")

            # Step 2: Poll for transcription status (async)
            transcription_result = await self._poll_transcription_status(transcription_id)

            # Step 3: Process the result
            if transcription_result.get("success") and transcription_result.get("status") == "COMPLETED":
                full_text = transcription_result.get("text", "")
                duration = transcription_result.get("duration", 0)
                language_used = transcription_result.get("language", "unknown")
                logger.info(f"Transcription completed (Lang: {language_used}). Text length: {len(full_text)}, Duration: {duration}s")

                # *** Important: Re-evaluate Segmentation ***
                # Check if the IVRIT.AI response contains actual segments with timestamps.
                # If it does, parse *those* instead of the manual approximation below.
                # Assuming for now it only returns full text and duration.
                api_segments = transcription_result.get("segments") # Check if 'segments' key exists
                if api_segments and isinstance(api_segments, list) and len(api_segments) > 0 and 'start_time' in api_segments[0]:
                     logger.info(f"Received {len(api_segments)} segments directly from API. Using API segmentation.")
                     processed_segments = [
                         {
                             "id": str(seg.get("id", i)), # Ensure ID is string
                             "start_time": float(seg["start_time"]), # Ensure float
                             "end_time": float(seg.get("end_time", seg["start_time"] + 1)) if seg.get("end_time") is not None else float(seg["start_time"] + 1), # Handle potential missing end_time, ensure float
                             "text": seg.get("text", ""),
                             "confidence": float(seg.get("confidence", 1.0)) # Ensure float
                         } for i, seg in enumerate(api_segments) if seg.get('start_time') is not None
                     ]
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

    async def _upload_file(self, audio_path: str) -> str:
        """Upload file to IVRIT.AI API using httpx and return transcription ID."""
        # Ensure headers include the API key
        if not self.headers:
             logger.error("Attempted to upload file without API key headers.")
             raise Exception("Transcription API key is missing.")

        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Uploading file: {audio_path} (Size: {file_size} bytes)")
            filename = os.path.basename(audio_path)
            # Use a general audio content type, API should ideally detect format
            content_type = 'audio/mpeg' # Or 'application/octet-stream' might be safer if format is unknown

            async with aiofiles.open(audio_path, "rb") as audio_file:
                files = {"file": (filename, await audio_file.read(), content_type)}

                # ADD LANGUAGE PARAMETER HERE
                # The API error indicates 'language' is required.
                # Assuming Hebrew ('HE') is the intended language based on project context.
                data = {"language": "HE"}
                # END ADD LANGUAGE PARAMETER


                logger.info(f"Making async POST request to: {self.base_url} with language='HE'")

                # Use the shared client instance
                response = await self.http_client.post(
                    self.base_url,
                    headers=self.headers,
                    files=files,
                    data=data # Pass the language data
                )

                logger.info(f"Response status code: {response.status_code}")
                response_text = response.text
                logger.info(f"Response content preview: {response_text[:500]}...") # Log more of response for debugging

                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx

                data = response.json()
                if data.get("success"):
                    # --- CORRECTED KEY NAME HERE ---
                    transcription_id = data.get("transcriptionId") # Use "transcriptionId"
                    # --- END CORRECTED KEY NAME ---
                    if not transcription_id:
                         # This case should ideally not happen if success is true and ID exists,
                         # but keeps the check in case API changes unexpectedly.
                         raise Exception("API returned success=true but transcriptionId key was not found or value is empty.")
                    return transcription_id
                else:
                    # Improved error message extraction from API response
                    error_msg = "Unknown API error after upload (success=false)"
                    if isinstance(data.get("error"), dict):
                         # Try to get specific error message from nested structure
                         error_msg = data["error"].get("language", [data["error"].get("message", error_msg)])[0] # Prioritize language error if present
                    elif isinstance(data.get("error"), str):
                         error_msg = data.get("error") # Sometimes it's a simple string

                    logger.error(f"API returned success=false: {error_msg}")
                    raise Exception(f"API error: {error_msg}")

        except httpx.HTTPStatusError as http_err:
             error_detail = f"HTTP error during upload: {http_err.response.status_code}"
             try:
                  # Try to parse error body for more detail
                  err_data = http_err.response.json()
                  if 'error' in err_data:
                       if isinstance(err_data['error'], str):
                            error_detail += f" - Detail: {err_data['error']}"
                       elif isinstance(err_data['error'], dict):
                             # Handle nested dictionary errors like language error
                             nested_errs = [f"{k}: {v}" for k, v in err_data['error'].items()]
                             error_detail += f" - Detail: {'; '.join(nested_errs)}"
                  elif 'detail' in err_data:
                       error_detail += f" - Detail: {err_data['detail']}"
             except Exception:
                  error_detail += f" - Body: {http_err.response.text[:200]}..." # Log raw body if JSON parse fails

             logger.error(error_detail)
             # Raise specific exceptions based on status code if needed, otherwise raise a general exception
             if http_err.response.status_code == 401 or http_err.response.status_code == 403:
                  raise Exception("Authentication failed with transcription API. Check API key.") from http_err
             elif http_err.response.status_code == 400:
                  # The language error is a 400, but we now send language.
                  # If we still get a 400, the error detail will be in the log.
                  raise Exception(f"Bad request sent to transcription API: {error_detail}") from http_err
             else:
                 raise Exception(f"HTTP error during upload: {http_err.response.status_code}") from http_err

        except httpx.RequestError as req_err: # Includes timeouts, connection errors
            logger.error(f"Network error during upload: {str(req_err)}")
            raise Exception(f"Network error communicating with IVRIT.AI API: {str(req_err)}") from req_err
        except Exception as e:
            # Catch any other unexpected errors during the file upload logic itself
            logger.error(f"Unexpected error during file upload preparation or initial API call: {str(e)}", exc_info=True)
            raise

    async def _poll_transcription_status(self, transcription_id: str) -> Dict[str, Any]:
        """Poll for transcription status using httpx until completion or failure."""
         # Ensure headers include the API key
        if not self.headers:
             logger.error("Attempted to poll status without API key headers.")
             raise Exception("Transcription API key is missing.")

        attempts = 0
        url = f"{self.base_url}?id={transcription_id}"

        while attempts < self.max_polling_attempts:
            try:
                logger.info(f"Polling transcription status: {url} (Attempt {attempts + 1}/{self.max_polling_attempts})")

                # Use the shared client instance
                # Use a shorter timeout for individual polls compared to the upload
                response = await self.http_client.get(url, headers=self.headers, timeout=45.0) # Increased poll timeout slightly
                response.raise_for_status() # Check for HTTP errors

                data = response.json()
                status = data.get("status")
                logger.info(f"Transcription ID {transcription_id} status: {status}")

                if status == "COMPLETED" or status == "FAILED":
                    return data
                elif status in ["IN_QUEUE", "PENDING", "IN_PROGRESS"]:
                    attempts += 1
                    # Exponential backoff for polling interval
                    wait_time = self.polling_interval * (1.2 ** min(attempts // 3, 5)) # Faster initial polling, then slow down
                    logger.info(f"Waiting {wait_time:.1f} seconds before next poll for ID {transcription_id}...")
                    await asyncio.sleep(wait_time) # Use async sleep
                else:
                    logger.warning(f"Unexpected status received for ID {transcription_id}: {status}. Treating as temporary issue and retrying.")
                    attempts += 1
                    await asyncio.sleep(self.polling_interval * 2) # Wait longer for unexpected status

            except httpx.HTTPStatusError as http_err:
                error_detail = f"HTTP error during polling status for ID {transcription_id}: {http_err.response.status_code}"
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
                     raise Exception(f"Polling failed: Transcription ID not found: {transcription_id}") from http_err
                elif http_err.response.status_code in [401, 403]:
                     raise Exception(f"Polling failed: Authentication error polling status (status {http_err.response.status_code})") from http_err
                elif 500 <= http_err.response.status_code < 600:
                     logger.warning(f"Server error ({http_err.response.status_code}) during polling for ID {transcription_id}, retrying...")
                     attempts += 1
                     await asyncio.sleep(self.polling_interval * 2.5) # Wait longer for server errors
                else: # Other client errors (4xx) are likely permanent
                     raise Exception(f"Polling failed: HTTP error polling status: {http_err.response.status_code}") from http_err

            except httpx.RequestError as req_err: # Includes timeouts, connection errors
                logger.warning(f"Network error during polling for ID {transcription_id}: {str(req_err)}. Retrying...")
                attempts += 1
                await asyncio.sleep(self.polling_interval * 1.5)

            except Exception as e:
                 logger.error(f"Unexpected error polling transcription status for ID {transcription_id}: {str(e)}", exc_info=True)
                 # Depending on the error, you might want to retry or fail immediately
                 # For now, let's retry after a delay
                 attempts += 1
                 await asyncio.sleep(self.polling_interval * 2)


        logger.error(f"Polling timed out after {self.max_polling_attempts} attempts for ID {transcription_id}")
        raise Exception(f"Transcription timed out after ~{int(self.max_polling_attempts * self.polling_interval / 60)} minutes.")

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