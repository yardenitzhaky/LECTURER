from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import os
import tempfile
import base64
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NoteLecture External Processing Service", version="1.0.2")

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
        "version": "1.0.2"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
