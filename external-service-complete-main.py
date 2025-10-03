from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import os
import tempfile
import base64
import httpx
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NoteLecture External Processing Service", version="1.0.3")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "NoteLecture External Processing"}


@app.post("/process-pdf/")
async def process_pdf(file: UploadFile = File(...)):
    """Process PDF and extract text from slides"""
    try:
        import fitz  # PyMuPDF
        logger.info(f"Processing PDF: {file.filename}")
        content = await file.read()

        pdf_document = fitz.open(stream=content, filetype="pdf")
        slides = []

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text()
            if text.strip():
                slides.append(text.strip())

        pdf_document.close()
        logger.info(f"Extracted {len(slides)} slides from PDF")
        return JSONResponse(content={"slides": slides, "count": len(slides)})

    except ImportError as e:
        logger.error(f"Missing dependency: {str(e)}")
        raise HTTPException(status_code=500, detail="PyMuPDF not installed")
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-audio/")
async def extract_audio(video_file: UploadFile = File(...)):
    """Extract audio from uploaded video file"""
    temp_video_path = None
    temp_audio_path = None

    try:
        try:
            from moviepy.editor import VideoFileClip
            has_moviepy = True
        except ImportError:
            has_moviepy = False
            logger.error("moviepy not available")
            raise HTTPException(
                status_code=500,
                detail="Audio extraction requires moviepy which is not installed"
            )

        logger.info(f"Extracting audio from: {video_file.filename} (size: {video_file.size if hasattr(video_file, 'size') else 'unknown'})")

        # Save uploaded video to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            content = await video_file.read()
            tmp_video.write(content)
            temp_video_path = tmp_video.name
            logger.info(f"Saved video to temp file: {temp_video_path} ({len(content)} bytes)")

        # Create temporary file for audio output
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
            temp_audio_path = tmp_audio.name

        # Extract audio using moviepy
        logger.info("Starting audio extraction with moviepy...")
        video = VideoFileClip(temp_video_path)

        if video.audio is None:
            video.close()
            raise ValueError("No audio track found in video file")

        # Extract audio to MP3
        video.audio.write_audiofile(temp_audio_path, codec='libmp3lame', logger=None, verbose=False)
        video.close()
        logger.info(f"Audio extracted to: {temp_audio_path}")

        # Read the audio file and encode as base64
        with open(temp_audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        logger.info(f"Audio file size: {len(audio_bytes)} bytes, base64 size: {len(audio_base64)} chars")

        return JSONResponse(content={
            "status": "success",
            "audio_format": "mp3",
            "audio_data": audio_base64,
            "file_size": len(audio_bytes),
            "message": "Audio extracted successfully"
        })

    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {str(e)}")

    finally:
        # Clean up temporary files
        for path in [temp_video_path, temp_audio_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    logger.info(f"Cleaned up temp file: {path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup {path}: {cleanup_error}")


@app.post("/download-extract-audio/")
async def download_extract_audio(video_url: str = Form(...)):
    """Download video from URL and extract audio"""
    try:
        try:
            import yt_dlp
            has_deps = True
        except ImportError as e:
            logger.error(f"Missing dependency: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Video download requires yt_dlp which is not installed"
            )

        logger.info(f"Downloading and extracting audio from: {video_url}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            logger.info(f"Using temporary directory: {tmp_dir}")

            # Configure yt-dlp to directly extract audio as MP3
            filename_template = "downloaded_audio"
            ydl_opts = {
                'format': 'worstaudio/worst',  # Get lowest quality for faster processing
                'outtmpl': os.path.join(tmp_dir, f'{filename_template}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',  # 128kbps MP3
                }],
                'quiet': True,
                'no_warnings': True,
                'extractaudio': True,
                'audioformat': 'mp3',
            }

            # Download and extract audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Starting download with yt-dlp...")
                ydl.download([video_url])
                logger.info("Download completed")

            # Find the generated MP3 file
            mp3_files = [f for f in os.listdir(tmp_dir) if f.endswith('.mp3')]
            logger.info(f"Found MP3 files: {mp3_files}")

            if not mp3_files:
                # List all files for debugging
                all_files = os.listdir(tmp_dir)
                logger.error(f"No MP3 files found. All files in temp dir: {all_files}")
                raise Exception("No MP3 file was generated by yt-dlp")

            # Use the first (and likely only) MP3 file
            audio_file_path = os.path.join(tmp_dir, mp3_files[0])
            logger.info(f"Using audio file: {audio_file_path}")

            # Read the audio data and encode as base64
            with open(audio_file_path, 'rb') as f:
                audio_bytes = f.read()
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            logger.info(f"Audio file size: {len(audio_bytes)} bytes, base64 size: {len(audio_base64)} chars")

            return JSONResponse(content={
                "status": "success",
                "audio_format": "mp3",
                "audio_data": audio_base64,
                "file_size": len(audio_bytes),
                "message": "Audio downloaded and extracted successfully"
            })

    except Exception as e:
        logger.error(f"Error downloading/extracting audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Download/extraction failed: {str(e)}")


@app.post("/match-slides/")
async def match_slides(
    video_file: UploadFile = File(...),
    slides_data: str = Form(...),
    transcription_data: str = Form(...)
):
    """Match transcription segments to presentation slides"""
    try:
        logger.info("Starting slide matching process")

        slides = json.loads(slides_data)
        transcription = json.loads(transcription_data)

        matches = []
        if slides and transcription:
            segments_per_slide = max(1, len(transcription) // len(slides))

            for i, slide in enumerate(slides):
                start_idx = i * segments_per_slide
                end_idx = min(start_idx + segments_per_slide, len(transcription))

                if start_idx < len(transcription):
                    matched_segments = transcription[start_idx:end_idx]

                    if matched_segments:
                        matches.append({
                            "slide_index": i,
                            "start_time": matched_segments[0].get("start", 0),
                            "end_time": matched_segments[-1].get("end", 0),
                            "transcript_indices": list(range(start_idx, end_idx))
                        })

        logger.info(f"Created {len(matches)} slide matches")
        return JSONResponse(content={"matches": matches})

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON data provided")
    except Exception as e:
        logger.error(f"Error matching slides: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEW: Complete end-to-end lecture processing endpoint
# ============================================================================

async def _process_lecture_complete(
    lecture_id: int,
    video_file_content: Optional[bytes],
    video_url: Optional[str],
    slides_data: List[Dict],
    backend_url: str,
    api_key: Optional[str] = None
):
    """
    Background task to process a complete lecture:
    1. Extract/download audio
    2. Transcribe audio (via RunPod)
    3. Match transcription to slides
    4. Send results back to main backend
    """
    try:
        logger.info(f"[Lecture {lecture_id}] Starting complete processing")

        # Prepare headers for backend communication
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Step 1: Extract or download audio
            logger.info(f"[Lecture {lecture_id}] Step 1: Audio extraction")

            if video_url:
                # Download from URL
                logger.info(f"[Lecture {lecture_id}] Downloading from URL: {video_url[:100]}...")
                audio_response = await client.post(
                    f"{os.getenv('SELF_URL', 'http://localhost:8080')}/download-extract-audio/",
                    data={"video_url": video_url}
                )
            elif video_file_content:
                # Video file was uploaded - extract audio from it
                logger.info(f"[Lecture {lecture_id}] Extracting audio from uploaded video ({len(video_file_content)} bytes)")
                files = {"video_file": ("video.mp4", video_file_content, "video/mp4")}
                audio_response = await client.post(
                    f"{os.getenv('SELF_URL', 'http://localhost:8080')}/extract-audio/",
                    files=files
                )
            else:
                raise Exception("Neither video_file nor video_url provided")

            audio_response.raise_for_status()
            audio_result = audio_response.json()

            if audio_result.get("status") != "success" or not audio_result.get("audio_data"):
                raise Exception("Audio extraction failed or returned no data")

            audio_base64 = audio_result["audio_data"]
            logger.info(f"[Lecture {lecture_id}] Audio extracted successfully")

            # Step 2: Transcribe audio via main backend (which calls RunPod)
            logger.info(f"[Lecture {lecture_id}] Step 2: Transcribing audio")

            transcribe_response = await client.post(
                f"{backend_url}/api/internal/transcribe-audio",
                json={"audio_data": audio_base64, "language": "he"},
                headers=headers
            )
            transcribe_response.raise_for_status()
            transcription_result = transcribe_response.json()

            transcription_segments = transcription_result.get("segments", [])
            logger.info(f"[Lecture {lecture_id}] Transcription complete: {len(transcription_segments)} segments")

            # Step 3: Match transcription to slides
            logger.info(f"[Lecture {lecture_id}] Step 3: Matching slides")

            # Simple matching algorithm
            matches = []
            if slides_data and transcription_segments:
                segments_per_slide = max(1, len(transcription_segments) // len(slides_data))

                for i, slide in enumerate(slides_data):
                    start_idx = i * segments_per_slide
                    end_idx = min(start_idx + segments_per_slide, len(transcription_segments))

                    if start_idx < len(transcription_segments):
                        matched_segments = transcription_segments[start_idx:end_idx]

                        if matched_segments:
                            # Attach slide_index to each segment
                            for seg in matched_segments:
                                seg['slide_index'] = i

                            matches.extend(matched_segments)

            logger.info(f"[Lecture {lecture_id}] Matching complete: {len(matches)} matched segments")

            # Step 4: Send results back to main backend
            logger.info(f"[Lecture {lecture_id}] Step 4: Sending results to backend")

            result_response = await client.post(
                f"{backend_url}/api/internal/complete-lecture-processing",
                json={
                    "lecture_id": lecture_id,
                    "segments": matches,
                    "status": "completed"
                },
                headers=headers
            )
            result_response.raise_for_status()

            logger.info(f"[Lecture {lecture_id}] Processing completed successfully!")

    except Exception as e:
        logger.error(f"[Lecture {lecture_id}] Processing failed: {str(e)}", exc_info=True)

        # Notify backend of failure
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{backend_url}/api/internal/complete-lecture-processing",
                    json={
                        "lecture_id": lecture_id,
                        "status": "failed",
                        "error": str(e)
                    },
                    headers=headers
                )
        except Exception as notify_error:
            logger.error(f"[Lecture {lecture_id}] Failed to notify backend of error: {notify_error}")


@app.post("/process-lecture-complete/")
async def process_lecture_complete(
    background_tasks: BackgroundTasks,
    lecture_id: int = Form(...),
    slides_data: str = Form(...),
    backend_url: str = Form(...),
    video_file: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """
    Complete lecture processing endpoint.
    This runs the entire pipeline in the background on Cloud Run.

    Parameters:
    - lecture_id: ID of the lecture being processed
    - video_file: Uploaded video file (multipart)
    - video_url: OR video URL (form data)
    - slides_data: JSON string of slides data [{"index": 0, "image_data": "..."}, ...]
    - backend_url: Main backend URL to send results back to
    - api_key: Optional API key for backend authentication
    """
    try:
        slides = json.loads(slides_data)

        # Read video file if provided
        video_content = None
        if video_file:
            video_content = await video_file.read()
            logger.info(f"[Lecture {lecture_id}] Received video file: {len(video_content)} bytes")

        # Add to background tasks (Cloud Run supports this properly unlike Vercel)
        background_tasks.add_task(
            _process_lecture_complete,
            lecture_id=lecture_id,
            video_file_content=video_content,
            video_url=video_url,
            slides_data=slides,
            backend_url=backend_url,
            api_key=api_key
        )

        logger.info(f"[Lecture {lecture_id}] Processing queued in background")

        return JSONResponse(content={
            "status": "processing",
            "message": f"Lecture {lecture_id} processing started in background",
            "lecture_id": lecture_id
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in slides_data: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid slides_data JSON")
    except Exception as e:
        logger.error(f"Error queuing lecture processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Detailed health check with dependency status"""
    dependencies = {}

    try:
        import fitz
        dependencies["pymupdf"] = True
    except ImportError:
        dependencies["pymupdf"] = False

    try:
        import moviepy
        dependencies["moviepy"] = True
    except ImportError:
        dependencies["moviepy"] = False

    try:
        import yt_dlp
        dependencies["yt_dlp"] = True
    except ImportError:
        dependencies["yt_dlp"] = False

    try:
        import cv2
        dependencies["opencv"] = True
    except ImportError:
        dependencies["opencv"] = False

    try:
        import numpy
        dependencies["numpy"] = True
    except ImportError:
        dependencies["numpy"] = False

    return {
        "status": "healthy",
        "dependencies": dependencies,
        "version": "1.0.3"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
