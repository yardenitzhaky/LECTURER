# app/services/transcription.py
import os
import time
# Remove requests import
# import requests
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
        }
        # Use an AsyncClient instance for connection pooling
        self.http_client = httpx.AsyncClient(timeout=60.0) # Increased timeout

        # How often to poll for status (in seconds)
        self.polling_interval = 12
        # Maximum polling attempts (adjust as needed)
        self.max_polling_attempts = 105

    # --- Synchronous Helper for extract_audio ---
    def _sync_extract_audio(self, video_path: str, output_audio_path: str):
        """Synchronous part of audio extraction."""
        try:
            logger.info(f"[Sync] Extracting audio from '{video_path}' to '{output_audio_path}'")
            with mp.VideoFileClip(video_path) as video:
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
            os.makedirs("uploads", exist_ok=True)
            filename = str(uuid4())
            output_path = os.path.join("uploads", f"{filename}.mp3")
            temp_path = os.path.join("uploads", f"{filename}.%(ext)s")

            logger.info(f"[Sync] Downloading from URL: {video_url}")
            logger.info(f"[Sync] Output will be saved to: {output_path}")

            ydl_opts = {
                'format': 'worstaudio/worst',
                'outtmpl': temp_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '64',
                }],
                'socket_timeout': 30,
                'retries': 5,
                'verbose': False,
                'quiet': True, # Suppress yt-dlp console output
                'noprogress': True, # Don't show progress bars
                'ffmpeg_location': os.getenv("FFMPEG_PATH"), # Optional: if ffmpeg not in PATH
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("[Sync] Starting download with yt-dlp")
                ydl.download([video_url])
                logger.info("[Sync] Download completed")

            if not os.path.exists(output_path):
                logger.warning(f"[Sync] Expected output file not found: {output_path}")
                potential_files = [f for f in os.listdir("uploads") if f.startswith(filename) and f.endswith('.mp3')]
                if potential_files:
                    logger.info(f"[Sync] Found potential MP3 file: {potential_files[0]}")
                    output_path = os.path.join("uploads", potential_files[0])
                else:
                     # Check if *any* file was downloaded (e.g., webm, m4a) before MP3 conversion happened or failed
                    all_potential = [f for f in os.listdir("uploads") if f.startswith(filename)]
                    if all_potential:
                         logger.error(f"[Sync] Found downloaded files ({all_potential}) but not the expected MP3. Postprocessing might have failed.")
                         raise FileNotFoundError(f"Downloaded file found ({all_potential[0]}), but MP3 conversion failed or was skipped.")
                    else:
                         raise FileNotFoundError(f"No downloaded file found with prefix {filename}")

            logger.info(f"[Sync] Successfully downloaded and extracted audio to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Sync] Error downloading video from URL: {str(e)}")
            logger.error(traceback.format_exc())
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
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found at path: {audio_path}")
            if not os.access(audio_path, os.R_OK):
                raise PermissionError(f"No permission to read audio file at: {audio_path}")

            # File format check/conversion (keep sync for now, usually fast unless huge file)
            base, ext = os.path.splitext(audio_path)
            if ext.lower() not in ['.mp3', '.wav', '.m4a', '.aac', '.flac']:
                logger.warning(f"File format {ext} may not be supported. Consider converting to MP3 if issues arise.")
                # Conversion logic removed for brevity, assuming input is mostly correct or API handles it.
                # If conversion is needed and slow, it should also use run_in_executor.

            # Step 1: Upload file to IVRIT.AI API (async)
            transcription_id = await self._upload_file(audio_path)
            logger.info(f"File uploaded successfully. Transcription ID: {transcription_id}")

            # Step 2: Poll for transcription status (async)
            transcription_result = await self._poll_transcription_status(transcription_id)

            # Step 3: Process the result
            if transcription_result.get("success") and transcription_result.get("status") == "COMPLETED":
                full_text = transcription_result.get("text", "")
                duration = transcription_result.get("duration", 0)
                logger.info(f"Transcription completed. Text length: {len(full_text)}, Duration: {duration}s")

                # *** Important: Re-evaluate Segmentation ***
                # Check if the IVRIT.AI response contains actual segments with timestamps.
                # If it does, parse *those* instead of the manual approximation below.
                # Assuming for now it only returns full text and duration.
                api_segments = transcription_result.get("segments") # Check if 'segments' key exists
                if api_segments and isinstance(api_segments, list) and len(api_segments) > 0 and 'start_time' in api_segments[0]:
                     logger.info(f"Received {len(api_segments)} segments directly from API. Using API segmentation.")
                     processed_segments = [
                         {
                             "id": seg.get("id", str(i)), # Use API ID if available
                             "start_time": seg["start_time"],
                             "end_time": seg.get("end_time"), # Handle potential missing end_time
                             "text": seg.get("text", ""),
                             "confidence": seg.get("confidence", 1.0)
                         } for i, seg in enumerate(api_segments) if seg.get('start_time') is not None
                     ]
                else:
                     logger.warning("API did not provide detailed segments. Approximating segmentation based on duration.")
                     # Keep the approximate segmentation logic as a fallback
                     segment_duration = 15
                     num_segments = max(1, int(duration / segment_duration)) if duration > 0 else 1
                     words = full_text.split()
                     words_per_segment = max(1, len(words) // num_segments) if num_segments > 0 else len(words)
                     processed_segments = []
                     for i in range(num_segments):
                         start_idx = i * words_per_segment
                         end_idx = min(len(words), (i + 1) * words_per_segment)
                         if start_idx >= len(words): break
                         segment_text = " ".join(words[start_idx:end_idx])
                         start_time = i * segment_duration
                         end_time = min(duration, (i + 1) * segment_duration) if duration > 0 else segment_duration
                         processed_segments.append({
                             "id": str(i + 1), "start_time": start_time, "end_time": end_time,
                             "text": segment_text, "confidence": 0.9 # Indicate lower confidence for approximation
                         })
                     if not processed_segments and full_text: # Handle case where duration might be 0 but text exists
                          processed_segments.append({
                              "id": "1", "start_time": 0, "end_time": 5, # Assign arbitrary short duration
                              "text": full_text, "confidence": 0.9
                          })


                return {
                    "segments": processed_segments,
                    "language": "he",
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
            logger.error(f"Error during transcription: {str(e)}", exc_info=True)
            raise

    async def _upload_file(self, audio_path: str) -> str:
        """Upload file to IVRIT.AI API using httpx and return transcription ID."""
        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Uploading file: {audio_path} (Size: {file_size} bytes)")
            filename = os.path.basename(audio_path)
            content_type = 'audio/wav' if audio_path.lower().endswith('.wav') else 'audio/mpeg'

            async with aiofiles.open(audio_path, "rb") as audio_file:
                files = {"file": (filename, await audio_file.read(), content_type)}
                logger.info(f"Making async POST request to: {self.base_url}")

                # Use the shared client instance
                response = await self.http_client.post(
                    self.base_url,
                    headers=self.headers,
                    files=files
                )

                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response content preview: {response.text[:200]}...")

                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx

                data = response.json()
                if data.get("success"):
                    return data.get("transcription_id")
                else:
                    error_msg = data.get("error", "Unknown API error after upload")
                    logger.error(f"API error: {error_msg}")
                    raise Exception(f"API error: {error_msg}")

        except httpx.HTTPStatusError as http_err:
             logger.error(f"HTTP error during upload: {http_err.response.status_code} - {http_err.response.text}")
             raise Exception(f"HTTP error during upload: {http_err.response.status_code}") from http_err
        except httpx.RequestError as req_err:
            logger.error(f"Network error during upload: {str(req_err)}")
            raise Exception(f"Network error communicating with IVRIT.AI API: {str(req_err)}") from req_err
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}", exc_info=True)
            raise

    async def _poll_transcription_status(self, transcription_id: str) -> Dict[str, Any]:
        """Poll for transcription status using httpx until completion or failure."""
        attempts = 0
        url = f"{self.base_url}?id={transcription_id}"

        while attempts < self.max_polling_attempts:
            try:
                logger.info(f"Polling transcription status: {url} (Attempt {attempts + 1}/{self.max_polling_attempts})")

                # Use the shared client instance
                response = await self.http_client.get(url, headers=self.headers, timeout=30)
                response.raise_for_status() # Check for HTTP errors

                data = response.json()
                status = data.get("status")
                logger.info(f"Transcription status: {status}")

                if status == "COMPLETED" or status == "FAILED":
                    return data
                elif status in ["IN_QUEUE", "PENDING", "IN_PROGRESS"]:
                    attempts += 1
                    wait_time = self.polling_interval * (1.2 ** min(attempts // 5, 5)) # Exponential backoff
                    logger.info(f"Waiting {wait_time:.1f} seconds before next poll...")
                    await asyncio.sleep(wait_time) # Use async sleep
                else:
                    logger.warning(f"Unexpected status received: {status}. Treating as temporary issue and retrying.")
                    attempts += 1
                    await asyncio.sleep(self.polling_interval * 2) # Wait longer for unexpected status

            except httpx.HTTPStatusError as http_err:
                logger.error(f"HTTP error during polling: {http_err.response.status_code} - {http_err.response.text}")
                if http_err.response.status_code == 404:
                     raise Exception(f"Transcription ID not found: {transcription_id}") from http_err
                elif http_err.response.status_code in [401, 403]:
                     raise Exception(f"Authentication error polling status (status {http_err.response.status_code})") from http_err
                elif 500 <= http_err.response.status_code < 600:
                     logger.warning(f"Server error ({http_err.response.status_code}) during polling, retrying...")
                     attempts += 1
                     await asyncio.sleep(self.polling_interval * 2)
                else: # Other client errors (4xx) are likely permanent
                     raise Exception(f"HTTP error polling status: {http_err.response.status_code}") from http_err

            except httpx.RequestError as req_err: # Includes timeouts, connection errors
                logger.warning(f"Network error during polling: {str(req_err)}. Retrying...")
                attempts += 1
                await asyncio.sleep(self.polling_interval * 1.5)

            except Exception as e:
                 logger.error(f"Unexpected error polling transcription status: {str(e)}", exc_info=True)
                 # Depending on the error, you might want to retry or fail immediately
                 # For now, let's retry after a delay
                 attempts += 1
                 await asyncio.sleep(self.polling_interval * 2)


        logger.error(f"Polling timed out after {self.max_polling_attempts} attempts for ID {transcription_id}")
        raise Exception(f"Transcription timed out after {(self.max_polling_attempts * self.polling_interval)} seconds (approx)")

    async def cleanup(self, audio_path: str):
        """Clean up temporary audio file asynchronously."""
        try:
            if os.path.exists(audio_path):
                 # Use aiofiles for async remove if needed, but os.remove is usually fast enough
                 # For simplicity, keeping os.remove, but wrap in executor if it proves slow on certain systems/filesystems
                 loop = asyncio.get_running_loop()
                 await loop.run_in_executor(None, os.remove, audio_path)
                 logger.info(f"Cleaned up temporary file: {audio_path}")
        except Exception as e:
            logger.error(f"Error cleaning up audio file '{audio_path}': {str(e)}")

    async def close_client(self):
        """Closes the httpx client. Call this during application shutdown."""
        await self.http_client.aclose()
        logger.info("HTTPX client closed.")

